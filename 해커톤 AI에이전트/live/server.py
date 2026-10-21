"""실시간 검사 영상 서버 — 카메라(또는 가상 컨베이어 영상)를 여는 곳은 여기 하나뿐이다.

한 프로세스 안에서:
  ① 영상 입력   영상 파일(반복 재생) 또는 웹캠에서 프레임을 읽는다 (느려지면 프레임을 건너뛰어 실시간 유지)
  ② 미리보기    매 프레임 화면 전체를 YOLO 로 보고 얇은 박스를 그린다 (보여주기용, 집계하지 않음)
  ③ 센싱 구역   기판(초록 영역)이 화면 가운데를 지나는 순간 한 번만 잘라 정식 검사 → 판정(코드 규칙)
                 → 기판에 판정 도장(OK / HOLD / NG)과 굵은 박스를 붙여 함께 흘려보낸다
  ④ 이벤트      판정 1건 = 이벤트 1개 → 보고 에이전트(큐, 뒤에서 한 건씩) · 라인 감시 에이전트
  ⑤ 내보내기    박스를 그린 영상을 MJPEG 로 내보낸다. 여러 화면이 동시에 봐도 카메라·검사는 한 번뿐
  ⑥ 기록        이상·의심 기판은 캡처 → Qwen 보고서 초안 → 검사 대장 '작업자 확인 대기' (대시보드에서 확정)

주소 (기본 포트 8506):
  /              전용 뷰어 (영상 + 현황, 프로젝터용 전체 화면)
  /stream.mjpg   박스·판정을 그린 영상
  /state         현황 JSON (카운트, 최근 판정, 경고, 보고서 상태)
  /control?cmd=pause|resume|restart|reset   /control?lang=ko|vi|en (보고서 문장 언어)
  /capture/<이름>.jpg   캡처 이미지

실행: .venv\\Scripts\\python -m live.server [--source videos/pcb_conveyor.mp4 | --camera 0] [--port 8506]
"""
import argparse
import json
import queue
import sys
import threading
import time
from collections import deque
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.detect import _model, detect, thresholds  # noqa: E402
from agent.pipeline import OUT, analyze_detected, register_pending  # noqa: E402

LIVE = OUT / 'live'
CAPTURES = LIVE / 'captures'
COLOR = {'reject': (40, 40, 225), 'review': (0, 150, 255), 'normal': (70, 175, 70)}    # BGR
STAMP = {'reject': 'NG', 'review': 'HOLD', 'normal': 'OK'}
ZONE_GRAY = (175, 175, 175)


class Line:
    """검사 라인 하나 (입력 1개 · 센싱 구역 1개)의 상태."""

    def __init__(self, a):
        self.a = a
        self.lock = threading.Lock()
        self.frame_cv = threading.Condition()
        self.jpeg = None
        self.frame_no = 0
        self.paused = False
        self.restart = False
        self.lang = a.lang
        # 정답 대조: 영상과 같은 이름의 json(가상 컨베이어 영상의 정답)이 있으면 판정마다 정답과 비교한다
        self.gt = None
        if a.camera is None:
            mf = Path(a.source).with_suffix('.json')
            if mf.exists():
                self.gt = json.loads(mf.read_text(encoding='utf-8'))
        g = self.gt or {}
        # 라인 종류(모델·지식 파일): --domain > 영상 json 의 domain > pcb
        self.domain = a.domain or g.get('domain', 'pcb')
        self.bw = g.get('board_w', g.get('board_px', a.board))     # 제품(센싱 구역) 크기 — PCB 640×640, 액정 960×540
        self.bh = g.get('board_h', g.get('board_px', a.board))
        self.belt = np.array(g['belt_bgr'], np.int16) if g.get('belt_bgr') else None   # 있으면 '벨트 색과 다른 곳' = 제품
        self.preview_imgsz = a.preview_imgsz or {'pcb': 1280}.get(self.domain, 640)   # 화면 속 제품이 학습 축척이 되도록
        self.conf = thresholds(self.domain)['conf_review']
        self.model = _model(self.domain)
        self.names = self.model.names
        self.reports = queue.Queue()
        self.xlsx_dirty = False
        self.reset()

    def reset(self):
        with self.lock:
            self.seq = 0
            self.counts = {'normal': 0, 'review': 0, 'reject': 0}
            self.events = deque(maxlen=40)      # 최근 판정 (최신이 앞)
            self.history = deque(maxlen=20)     # 라인 감시용 (판정, 유형, 위치)
            self.alerts = deque(maxlen=12)
            self.cooldown = {}
            self.boards = []                    # 판정이 붙어 흘러가는 기판
            self.prev_centers = []
            self.flash = 0
            self.flash_color = ZONE_GRAY
            self.fps = 0.0
            self.infer_ms = 0.0
            self.preview_every = 1
            self.eval = {'boards': 0, 'correct': 0, 'defect_boards': 0, 'defect_caught': 0, 'normal_boards': 0,
                         'normal_passed': 0, 'tp': 0, 'fp': 0, 'fn': 0, 'unmatched': 0}
            self.eval_log = None                # 이번 재생의 대조 기록 파일 (처음 판정할 때 만든다)

    # ── 제품 찾기: PCB 는 벨트(회색) 위의 초록 영역, 그 밖에는 벨트 색과 다른 영역 ─────────
    def segments(self, frame, step=4):
        """제품 위치 → [{'x0','x1','y0','y1','cx','touch'}]. 빠르게 하려고 1/step 로 줄인 화면에서 찾고 좌표만 되돌린다 (±step px)."""
        small = frame[::step, ::step]
        if self.belt is not None:
            mask = np.abs(small.astype(np.int16) - self.belt).max(axis=2) > 45
            mask[:30 // step], mask[-30 // step:] = False, False     # 위아래 레일 제외
        else:
            b, g, r = (small[..., i].astype(np.int16) for i in range(3))
            mask = (g - np.maximum(r, b)) > 25
        return [{**s, 'x0': s['x0'] * step, 'x1': min(s['x1'] * step, frame.shape[1]), 'y0': s['y0'] * step,
                 'y1': min(s['y1'] * step, frame.shape[0]), 'cx': s['cx'] * step} for s in self._runs(mask)]

    @staticmethod
    def _runs(mask):
        occ = mask.mean(axis=0) > 0.25                       # 열마다 초록 비율
        segs, x = [], 0
        w = len(occ)
        while x < w:
            if occ[x]:
                x0 = x
                while x < w and occ[x]:
                    x += 1
                if x - x0 > 40:
                    rows = np.nonzero(mask[:, x0:x].mean(axis=1) > 0.25)[0]
                    if len(rows):
                        segs.append({'x0': x0, 'x1': x, 'y0': int(rows[0]), 'y1': int(rows[-1]) + 1,
                                     'cx': (x0 + x) / 2, 'touch': x0 == 0 or x == w})
            x += 1
        return segs

    # ── 정식 검사 (센싱 구역) ────────────────────────────────────────
    def compare(self, fidx, x0, y0, det):
        """판정 1건을 영상 정답과 비교 → {'kind', 'gt_types', 'ok', 'tp', 'fp', 'fn'} (정답이 없으면 None).

        기판 맞추기: 기판 중심이 화면 가운데 오는 프레임(center_frame)이 지금 프레임에 가장 가까운 기판.
        결함 맞추기: 같은 종류 + IoU ≥ 0.5 (tools/eval_conveyor.py 와 같은 기준).
        """
        if not self.gt or fidx is None:
            return None
        b = min(self.gt['boards'], key=lambda b: abs(b['center_frame'] - fidx))
        if abs(b['center_frame'] - fidx) > 20:
            self.eval['unmatched'] += 1
            return None
        sw, sh, speed = self.bw, self.bh, self.gt['speed_px_per_frame']
        bx = round(b['x0'] - fidx * speed)                  # 이 프레임에서 제품 왼쪽 x
        gt = [(l['type'], [(l['cx'] - l['w'] / 2) * sw + bx - x0, (l['cy'] - l['h'] / 2) * sh + b['y'] - y0,
                           (l['cx'] + l['w'] / 2) * sw + bx - x0, (l['cy'] + l['h'] / 2) * sh + b['y'] - y0])
              for l in b['labels']]

        def iou(p, q):
            ix = max(0, min(p[2], q[2]) - max(p[0], q[0]))
            iy = max(0, min(p[3], q[3]) - max(p[1], q[1]))
            inter = ix * iy
            return inter / ((p[2] - p[0]) * (p[3] - p[1]) + (q[2] - q[0]) * (q[3] - q[1]) - inter + 1e-9)

        used, tp = set(), 0
        for d in sorted(det['defects'], key=lambda d: -d['conf']):
            cand = [(iou(d['box_px'], g), j) for j, (t, g) in enumerate(gt) if j not in used and t == d['type']]
            best = max(cand, default=(0, None))
            if best[0] >= 0.5:
                used.add(best[1])
                tp += 1
        fp, fn = len(det['defects']) - tp, len(gt) - tp
        ok = (det['verdict'] != 'normal') if b['kind'] == 'defect' else (det['verdict'] == 'normal')
        e = self.eval
        e['boards'] += 1
        e['correct'] += ok
        e[f'{b["kind"]}_boards'] += 1
        e['defect_caught' if b['kind'] == 'defect' else 'normal_passed'] += ok
        e['tp'] += tp
        e['fp'] += fp
        e['fn'] += fn
        return {'board': b['index'], 'kind': b['kind'], 'gt_types': sorted({t for t, _ in gt}), 'ok': bool(ok),
                'tp': tp, 'fp': fp, 'fn': fn}

    def _log_eval(self, ev):
        """정답 대조 기록 (outputs/live/eval_<시작 시각>.csv) — 재생이 끝난 뒤 한 장씩 다시 볼 수 있게."""
        import csv
        if self.eval_log is None:
            LIVE.mkdir(parents=True, exist_ok=True)
            self.eval_log = LIVE / f'eval_{datetime.now():%Y%m%d_%H%M%S}.csv'
            with open(self.eval_log, 'w', newline='', encoding='utf-8-sig') as f:
                csv.writer(f).writerow(['seq', 'time', 'video_board', 'gt_kind', 'gt_types', 'verdict', 'pred_types',
                                        'board_ok', 'tp', 'fp', 'fn', 'capture'])
        g = ev['gt']
        with open(self.eval_log, 'a', newline='', encoding='utf-8-sig') as f:
            csv.writer(f).writerow([ev['seq'], ev['time'], g['board'], g['kind'], ' '.join(g['gt_types']), ev['verdict'],
                                    ' '.join(ev['types']), int(g['ok']), g['tp'], g['fp'], g['fn'], ev['name']])

    def inspect(self, frame, seg, fidx=None):
        sw, sh = self.bw, self.bh
        cx, cy = int(round(seg['cx'])), (seg['y0'] + seg['y1']) // 2
        h, w = frame.shape[:2]
        x0 = min(max(cx - sw // 2, 0), w - sw)
        y0 = min(max(cy - sh // 2, 0), h - sh)
        crop = frame[y0:y0 + sh, x0:x0 + sw].copy()
        with self.lock:
            self.seq += 1
            seq = self.seq
        stamp = datetime.now()
        name = f'live_{stamp:%Y%m%d_%H%M%S}_{seq:04d}'
        CAPTURES.mkdir(parents=True, exist_ok=True)
        path = CAPTURES / f'{name}.jpg'
        cv2.imwrite(str(path), crop, [cv2.IMWRITE_JPEG_QUALITY, 95])
        det = detect(path, self.domain, save_dir=OUT / 'work' / name, tile=False)
        verdict = det['verdict']
        types = sorted({d['type'] for d in det['defects']})
        ev = {'seq': seq, 'name': name, 'time': stamp.strftime('%H:%M:%S'), 'verdict': verdict, 'types': types,
              'n': len(det['defects']), 'max_conf': max((d['conf'] for d in det['defects']), default=0.0),
              'capture': f'/capture/{name}.jpg', 'report': 'none' if verdict == 'normal' else 'queued'}
        with self.lock:
            ev['gt'] = self.compare(fidx, x0, y0, det)
            if ev['gt']:
                self._log_eval(ev)
            self.counts[verdict] += 1
            self.events.appendleft(ev)
            self.flash, self.flash_color = 10, COLOR[verdict]
            self.boards.append({'seq': seq, 'verdict': verdict, 'cx': seg['cx'], 'off': x0 - seg['cx'], 'y0': y0,
                                'defects': [(d['box_px'], d['type'], d['conf'], d['level']) for d in det['defects']]})
            self.monitor(verdict, det['defects'], seq)
        if verdict != 'normal':
            self.reports.put((det, name, seq))

    # ── 라인 감시 에이전트: 한 장이 아니라 흐름을 본다 ──────────────────
    def monitor(self, verdict, defects, seq):
        """규칙: 연속 불량 / 같은 유형 반복 / 같은 위치 반복 / 최근 불량률. 같은 경고는 일정 기판 수 동안 다시 내지 않는다."""
        types = {d['type'] for d in defects if d['level'] == 'reject'}
        cells = {(d['type'], d['position']) for d in defects if d['level'] == 'reject'}
        self.history.append((verdict, types, cells))
        h = list(self.history)

        found = []                              # (우선순위, 종류, 인자) — 기판 하나에 경고는 하나만

        def fire(kind, key, **args):
            if seq - self.cooldown.get(kind, -999) >= 8:
                found.append(({'location_repeat': 0, 'streak': 1, 'type_repeat': 2, 'ng_rate': 3}[kind], kind, args))

        streak = 0
        for v, _, _ in reversed(h):
            if v != 'reject':
                break
            streak += 1
        if streak >= 4:
            fire('streak', 'ng', n=streak)
        last5 = h[-5:]
        for t in types:
            n = sum(t in ts for _, ts, _ in last5)
            if n >= 3:
                fire('type_repeat', t, type=t, n=n, of=len(last5))
        for c in cells:
            n = sum(c in cs for _, _, cs in last5)
            if n >= 3:
                fire('location_repeat', f'{c[0]}@{c[1]}', type=c[0], position=c[1], n=n, of=len(last5))
        if len(h) >= 10:
            rate = sum(v == 'reject' for v, _, _ in h) / len(h)
            if rate >= 0.9:
                fire('ng_rate', 'rate', rate=round(rate, 2), n=len(h))
        if found:
            _, kind, args = min(found, key=lambda f: f[0])
            self.cooldown[kind] = seq
            self.alerts.appendleft({'seq': seq, 'time': datetime.now().strftime('%H:%M:%S'), 'kind': kind, **args})

    # ── 보고 에이전트 (뒤에서 한 건씩): 지식 조회 + Qwen 초안 → 대장 '확인 대기' ──
    def report_worker(self):
        while True:
            det, name, seq = self.reports.get()
            self._report_status(seq, 'writing')
            self.preview_every = 2              # Qwen 이 GPU 를 쓰는 동안 미리보기를 줄여 영상이 끊기지 않게
            meta = {'part_no': f'LINE1-{seq:04d}', 'lot': f'L{datetime.now():%Y%m%d}-LIVE'}
            # Qwen 은 한 건에 10초 남짓, 기판은 2초마다 온다 → 밀리면 AI 문장 없이 대장에만 바로 기록
            # (대시보드에서 [문장 다시 생성]으로 나중에 쓸 수 있다). 이상(reject)을 의심보다 먼저 쓴다.
            backlog = self.reports.qsize()
            use_llm = backlog <= self.a.max_backlog or (det['verdict'] == 'reject' and backlog <= 2 * self.a.max_backlog)
            try:
                try:
                    if not use_llm:
                        raise RuntimeError('backlog')
                    result = analyze_detected(det, name, lang=self.lang, meta=meta, source='live')
                    status = 'ready'
                except Exception as e:  # noqa: BLE001 — 밀렸거나 Ollama 가 꺼져 있으면 문장 없이 기록만
                    result = {'name': name, 'work': str(OUT / 'work' / name), 'part_info': '', 'meta': meta,
                              'lang': self.lang, 'detection': det, 'source': 'live',
                              'text': {'summary': '', 'defects': [], 'causes': []}}
                    from agent.pipeline import refresh
                    refresh(result, write=False)
                    status = 'logged' if str(e) == 'backlog' else 'no_llm'
                register_pending(result, xlsx=False)    # 엑셀 대장은 xlsx_worker 가 20초마다 모아서
                self.xlsx_dirty = True
                self._report_status(seq, status)
            except Exception as e:  # noqa: BLE001
                self._report_status(seq, 'error')
                print('report error:', e)
            finally:
                if self.reports.empty():
                    self.preview_every = 1

    def xlsx_worker(self, every=20):
        """엑셀 대장(썸네일 포함)은 다시 만드는 데 몇 초 걸려서, 실시간 기록은 모아서 주기적으로 다시 만든다."""
        from agent.records import rebuild_xlsx
        while True:
            time.sleep(every)
            if self.xlsx_dirty:
                self.xlsx_dirty = False
                try:
                    rebuild_xlsx(OUT)
                except Exception as e:  # noqa: BLE001
                    print('xlsx error:', e)

    def _report_status(self, seq, status):
        with self.lock:
            for ev in self.events:
                if ev['seq'] == seq:
                    ev['report'] = status

    # ── 그리기 ───────────────────────────────────────────────────────
    def draw(self, frame, segs, preview):
        h, w = frame.shape[:2]
        zx0, zx1 = (w - self.bw) // 2, (w + self.bw) // 2
        overlay = frame.copy()
        # 미리보기 박스: 아직 검사 전인 기판만 얇게 (화면 가장자리에 걸친 기판은 흐리게)
        inspected = [(b['cx'] + b['off'], b['cx'] + b['off'] + self.bw) for b in self.boards]
        for (x0, y0, x1, y1), c, conf in preview:
            mx = (x0 + x1) / 2
            if any(a <= mx <= b for a, b in inspected):
                continue
            seg = next((s for s in segs if s['x0'] <= mx <= s['x1']), None)
            faint = seg is None or seg['touch']              # 화면 가장자리에 걸친 기판은 흐리게
            col = (190, 190, 190) if faint else (255, 255, 0)  # 미리보기 = 하늘색 (판정 전)
            cv2.rectangle(overlay, (int(x0), int(y0)), (int(x1), int(y1)), col, 2, cv2.LINE_AA)
            label = f'{self.names[c]} {conf:.2f}'
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            ty = max(int(y0) - 4, th + 4)
            cv2.rectangle(overlay, (int(x0), ty - th - 4), (int(x0) + tw + 4, ty + 2), (30, 30, 30), -1)
            cv2.putText(overlay, label, (int(x0) + 2, ty - 1), cv2.FONT_HERSHEY_SIMPLEX, 0.45, col, 1, cv2.LINE_AA)
        frame = cv2.addWeighted(overlay, 0.9 if preview else 1.0, frame, 0.1 if preview else 0.0, 0)
        # 센싱 구역
        zc = self.flash_color if self.flash > 0 else ZONE_GRAY
        thick = 4 if self.flash > 0 else 2
        cv2.rectangle(frame, (zx0, 30), (zx1, h - 30), zc, thick, cv2.LINE_AA)
        for x in (zx0, zx1):
            cv2.line(frame, (x, 30), (x, h - 30), zc, thick, cv2.LINE_AA)
        cv2.putText(frame, 'SENSING ZONE', (zx0 + 8, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.55, zc, 2, cv2.LINE_AA)
        # 판정이 붙은 기판: 굵은 박스 + 도장
        for b in self.boards:
            bx = int(round(b['cx'] + b['off']))
            for (x0, y0, x1, y1), t, conf, level in b['defects']:
                p0, p1 = (bx + x0, b['y0'] + y0), (bx + x1, b['y0'] + y1)
                cv2.rectangle(frame, p0, p1, COLOR[level], 2, cv2.LINE_AA)
                cv2.putText(frame, f'{t} {conf:.2f}', (p0[0], p0[1] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                            COLOR[level], 1, cv2.LINE_AA)
            label = f'#{b["seq"]} {STAMP[b["verdict"]]}'
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_DUPLEX, 1.0, 2)
            sx, sy = bx + 14, b['y0'] + 14
            cv2.rectangle(frame, (sx, sy), (sx + tw + 18, sy + th + 18), COLOR[b['verdict']], -1)
            cv2.putText(frame, label, (sx + 9, sy + th + 9), cv2.FONT_HERSHEY_DUPLEX, 1.0, (255, 255, 255), 2,
                        cv2.LINE_AA)
        # 라이브 표시
        cv2.circle(frame, (24, 22), 7, (40, 40, 225) if not self.paused else (150, 150, 150), -1)
        cv2.putText(frame, f'LIVE  {self.fps:4.1f} fps  {self.infer_ms:4.0f} ms', (38, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (235, 235, 235), 1, cv2.LINE_AA)
        if self.paused:
            cv2.putText(frame, 'PAUSED', (w - 130, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (235, 235, 235), 2, cv2.LINE_AA)
        return frame

    # ── 메인 루프 ────────────────────────────────────────────────────
    def open(self):
        if self.a.camera is not None:
            cap = cv2.VideoCapture(self.a.camera, cv2.CAP_DSHOW)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            return cap, None
        cap = cv2.VideoCapture(str(self.a.source))
        return cap, cap.get(cv2.CAP_PROP_FPS) or 30

    def run(self):
        cap, src_fps = self.open()
        if not cap.isOpened():
            sys.exit(f'cannot open source: {self.a.camera if self.a.camera is not None else self.a.source}')
        t0, idx = time.time(), 0
        last = None
        preview, preview_age = [], 0
        tick = deque(maxlen=30)
        while True:
            if self.restart:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                t0, idx, self.restart = time.time(), 0, False
                with self.lock:
                    self.boards, self.prev_centers = [], []
            if self.paused and last is not None:
                self.publish(self.draw(last.copy(), self.segments(last), preview))
                time.sleep(0.1)
                t0 = time.time() - idx / src_fps if src_fps else t0
                continue
            if src_fps:                          # 영상 파일: 실시간 속도에 맞춰 늦으면 건너뜀
                target = int((time.time() - t0) * src_fps)
                while idx < target - 1:
                    if not cap.grab():
                        break
                    idx += 1
                if idx > target:
                    time.sleep((idx - target) / src_fps)
            ok, frame = cap.read()
            if not ok:
                if self.a.camera is None and self.a.loop:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    t0, idx = time.time(), 0
                    with self.lock:
                        self.boards, self.prev_centers = [], []
                    continue
                time.sleep(0.05)
                continue
            idx += 1
            last = frame
            ts = time.time()
            segs = self.segments(frame)
            # 기판 이동 → 판정 붙은 기판 위치 갱신
            zc = frame.shape[1] / 2
            with self.lock:
                kept = []
                for b in self.boards:
                    m = [s for s in segs if -40 <= b['cx'] - s['cx'] <= 120]
                    if m:
                        b['cx'] = min(m, key=lambda s: b['cx'] - s['cx'])['cx']
                        kept.append(b)
                self.boards = kept
            # 센싱: 기판 중심이 화면 가운데를 지나는 순간 한 번
            for s in segs:
                if s['touch'] or s['x1'] - s['x0'] < 0.8 * self.bw:
                    continue
                prev = [p for p in self.prev_centers if 0 <= p - s['cx'] <= 120]
                if prev and min(prev) > zc >= s['cx']:
                    self.inspect(frame, s, idx - 1 if self.a.camera is None else None)
            self.prev_centers = [s['cx'] for s in segs]
            # 미리보기 (화면 전체, 원래 크기로)
            preview_age += 1
            if preview_age >= self.preview_every:
                preview_age = 0
                r = self.model.predict(frame, imgsz=self.preview_imgsz, conf=self.conf, verbose=False)[0]
                preview = [(b.tolist(), int(c), float(p)) for b, c, p in zip(r.boxes.xyxy, r.boxes.cls, r.boxes.conf)]
            self.infer_ms = 0.8 * self.infer_ms + 0.2 * (time.time() - ts) * 1000
            if self.flash > 0:
                self.flash -= 1
            tick.append(time.time())
            if len(tick) > 1:
                self.fps = (len(tick) - 1) / (tick[-1] - tick[0])
            self.publish(self.draw(frame, segs, preview))
            self.frame_no += 1

    def publish(self, img):
        ok, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if ok:
            with self.frame_cv:
                self.jpeg = buf.tobytes()
                self.frame_cv.notify_all()

    def _eval_summary(self):
        if not self.gt:
            return None
        e = self.eval
        p = e['tp'] / (e['tp'] + e['fp']) if e['tp'] + e['fp'] else 0.0
        r = e['tp'] / (e['tp'] + e['fn']) if e['tp'] + e['fn'] else 0.0
        return {**e, 'board_acc': round(e['correct'] / e['boards'], 4) if e['boards'] else None,
                'precision': round(p, 4), 'recall': round(r, 4), 'f1': round(2 * p * r / (p + r), 4) if p + r else 0.0,
                'total_boards': len(self.gt['boards']), 'log': self.eval_log.name if self.eval_log else None}

    def state(self):
        with self.lock:
            return {'running': True, 'paused': self.paused, 'lang': self.lang, 'fps': round(self.fps, 1),
                    'infer_ms': round(self.infer_ms, 1), 'inspected': self.seq, 'counts': dict(self.counts),
                    'queue': self.reports.qsize(), 'events': list(self.events), 'alerts': list(self.alerts),
                    'eval': self._eval_summary(),
                    'source': 'camera' if self.a.camera is not None else Path(self.a.source).name,
                    'domain': self.domain}


LINE = None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            try:
                while True:
                    with LINE.frame_cv:
                        LINE.frame_cv.wait(timeout=2)
                        jpg = LINE.jpeg
                    if jpg:
                        self.wfile.write(b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: '
                                         + str(len(jpg)).encode() + b'\r\n\r\n' + jpg + b'\r\n')
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                return
        elif u.path == '/state':
            self._send(200, json.dumps(LINE.state(), ensure_ascii=False).encode(), 'application/json; charset=utf-8')
        elif u.path == '/control':
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            cmd = q.get('cmd')
            if cmd == 'pause':
                LINE.paused = True
            elif cmd == 'resume':
                LINE.paused = False
            elif cmd == 'restart':
                LINE.restart, LINE.paused = True, False
            elif cmd == 'reset':
                LINE.reset()
                LINE.restart = True
            if q.get('lang') in ('ko', 'vi', 'en'):
                LINE.lang = q['lang']
            self._send(200, b'{"ok": true}', 'application/json')
        elif u.path.startswith('/capture/'):
            p = CAPTURES / Path(u.path).name
            if p.suffix == '.jpg' and p.exists() and p.parent == CAPTURES:
                self._send(200, p.read_bytes(), 'image/jpeg')
            else:
                self._send(404, b'not found', 'text/plain')
        elif u.path in ('/', '/index.html'):
            self._send(200, (Path(__file__).parent / 'viewer.html').read_bytes(), 'text/html; charset=utf-8')
        else:
            self._send(404, b'not found', 'text/plain')


def main():
    global LINE
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', default=str(ROOT / 'videos/pcb_conveyor.mp4'))
    ap.add_argument('--camera', type=int, default=None, help='웹캠 번호 (주면 영상 파일 대신 웹캠)')
    ap.add_argument('--port', type=int, default=8506)
    ap.add_argument('--line', choices=['pcb', 'phone'], default=None,
                    help='라인 이름 → videos/<line>_conveyor.mp4 를 입력으로 (--source 대신)')
    ap.add_argument('--domain', choices=['pcb', 'msdd', 'mobile'], default=None,
                    help='검사 모델 (기본: 영상 json 의 domain, 없으면 pcb)')
    ap.add_argument('--board', type=int, default=640, help='제품(센싱 구역) 크기 px — 영상 json 에 있으면 그 값을 쓴다')
    ap.add_argument('--preview-imgsz', type=int, default=None,
                    help='미리보기 추론 크기 (기본: PCB 1280 = 화면 원래 크기, 그 밖 640 = 제품이 학습 축척)')
    ap.add_argument('--lang', default='ko', choices=['ko', 'vi', 'en'])
    ap.add_argument('--max-backlog', type=int, default=2, help='보고서 대기가 이보다 많으면 AI 문장 없이 바로 기록')
    ap.add_argument('--no-loop', dest='loop', action='store_false')
    a = ap.parse_args()
    if a.line:
        a.source = str(ROOT / f'videos/{a.line}_conveyor.mp4')
    LINE = Line(a)
    threading.Thread(target=LINE.report_worker, daemon=True).start()
    threading.Thread(target=LINE.xlsx_worker, daemon=True).start()
    threading.Thread(target=LINE.run, daemon=True).start()
    srv = ThreadingHTTPServer(('0.0.0.0', a.port), Handler)
    srv.daemon_threads = True
    print(f'live server: http://localhost:{a.port}/  (stream /stream.mjpg, state /state)')
    srv.serve_forever()


if __name__ == '__main__':
    main()
