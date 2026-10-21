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

from agent.detect import MODELS, _model, detect, thresholds  # noqa: E402
from agent import line_router, records  # noqa: E402
from agent.pipeline import OUT, analyze_detected, load_result, needs_text, refresh, register_pending  # noqa: E402

LIVE = OUT / 'live'
CAPTURES = LIVE / 'captures'
COLOR = {'reject': (40, 40, 225), 'review': (0, 150, 255), 'normal': (70, 175, 70)}    # BGR
STAMP = {'reject': 'NG', 'review': 'HOLD', 'normal': 'OK'}
SHORT = {'pcb': 'PCB', 'msdd': 'METAL', 'mobile': 'LCD'}               # 혼합 라인 도장에 붙이는 제품 종류
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
        # 혼합 라인: 제품마다 종류·크기가 다르다 → 센싱 때 분배 에이전트(agent/line_router.py)가 정한다
        self.mixed = self.domain == 'mixed'
        self.sizes = ({d: tuple(s) for d, s in g['sizes'].items()} if self.mixed else {self.domain: (self.bw, self.bh)})
        ws = [w for w, _ in self.sizes.values()]
        self.zone_w = max(ws)
        self.min_w, self.join_gap, self.join_max = 0.8 * min(ws), 0.25 * min(ws), 1.15 * max(ws)
        if self.mixed:
            self.models = {d: _model(d) for d in self.sizes}    # 세 모델을 미리 올려 둔다 (첫 제품에서 멈추지 않게)
        else:
            self.preview_imgsz = a.preview_imgsz or {'pcb': 1280, 'msdd': 1280}.get(self.domain, 640)   # 화면 속 제품이 학습 축척이 되도록
            self.conf = thresholds(self.domain)['conf_review']
            self.model = _model(self.domain)
            self.names = self.model.names
        self.reports = queue.Queue()
        self.xlsx_dirty = False
        self.preview, self.preview_age = [], 0  # 미리보기 박스 (preview_every 프레임마다 갱신)
        self.tick = deque(maxlen=30)
        self.last_inspect = 0.0                 # 마지막으로 제품을 판정한 시각 (미리 쓰기는 라인이 쉴 때만)
        self.prefetched = set()                 # 미리 쓰기를 시도한 기록 (실패해도 다시 붙잡지 않게)
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
                         'normal_passed': 0, 'tp': 0, 'fp': 0, 'fn': 0, 'unmatched': 0, 'routed_ok': 0}
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
        segs = self._join(self._runs(mask), self.join_gap / step, self.join_max / step)
        return [{**s, 'x0': s['x0'] * step, 'x1': min(s['x1'] * step, frame.shape[1]), 'y0': s['y0'] * step,
                 'y1': min(s['y1'] * step, frame.shape[0]), 'cx': s['cx'] * step} for s in segs]

    @staticmethod
    def _join(segs, gap, max_w):
        """제품 색이 벨트와 비슷한 부분(예: 회색 금속면)에서 한 제품이 둘로 갈라진 경우를 다시 잇는다.
        틈이 제품 폭의 25% 이하이고 이은 폭이 제품 하나(115%)를 넘지 않을 때만 — 이웃 제품끼리는 붙지 않는다.
        혼합 라인은 틈은 가장 작은 제품, 폭은 가장 큰 제품 기준."""
        out = []
        for s in segs:
            p = out[-1] if out else None
            if p and s['x0'] - p['x1'] <= gap and s['x1'] - p['x0'] <= max_w:
                out[-1] = {'x0': p['x0'], 'x1': s['x1'], 'y0': min(p['y0'], s['y0']), 'y1': max(p['y1'], s['y1']),
                           'cx': (p['x0'] + s['x1']) / 2, 'touch': p['touch'] or s['touch']}
            else:
                out.append(s)
        return out

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
        sw, sh = b.get('board_w', self.bw), b.get('board_h', self.bh)     # 혼합 라인은 제품마다 크기가 다르다
        speed = self.gt['speed_px_per_frame']
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
        out = {'board': b['index'], 'kind': b['kind'], 'gt_types': sorted({t for t, _ in gt}), 'ok': bool(ok),
               'tp': tp, 'fp': fp, 'fn': fn}
        if self.mixed:                                       # 분배 에이전트가 제품 종류를 맞혔는지
            out['domain'] = b['domain']
            e['routed_ok'] += det['domain'] == b['domain']
        return out

    def _log_eval(self, ev):
        """정답 대조 기록 (outputs/live/eval_<시작 시각>.csv) — 재생이 끝난 뒤 한 장씩 다시 볼 수 있게."""
        import csv
        if self.eval_log is None:
            LIVE.mkdir(parents=True, exist_ok=True)
            self.eval_log = LIVE / f'eval_{datetime.now():%Y%m%d_%H%M%S}.csv'
            with open(self.eval_log, 'w', newline='', encoding='utf-8-sig') as f:
                csv.writer(f).writerow(['seq', 'time', 'video_board', 'gt_kind', 'gt_types', 'verdict', 'pred_types',
                                        'board_ok', 'tp', 'fp', 'fn', 'capture']
                                       + (['gt_domain', 'domain', 'route_rule'] if self.mixed else []))
        g = ev['gt']
        with open(self.eval_log, 'a', newline='', encoding='utf-8-sig') as f:
            csv.writer(f).writerow([ev['seq'], ev['time'], g['board'], g['kind'], ' '.join(g['gt_types']), ev['verdict'],
                                    ' '.join(ev['types']), int(g['ok']), g['tp'], g['fp'], g['fn'], ev['name']]
                                   + ([g['domain'], ev['domain'], ev['route']] if self.mixed else []))

    def route(self, frame, seg, step=2):
        """분배 에이전트: 제품 상자 안 화면(1/step 로 줄여서) → line_router.route."""
        region = frame[seg['y0']:seg['y1']:step, int(seg['x0']):int(seg['x1']):step]
        return line_router.route(region, seg['x1'] - seg['x0'], seg['y1'] - seg['y0'])

    def inspect(self, frame, seg, fidx=None):
        domain, route = self.domain, None
        if self.mixed:
            route = self.route(frame, seg)
            domain = route['domain']
        sw, sh = self.sizes[domain]
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
        det = detect(path, domain, save_dir=OUT / 'work' / name, tile=False)
        verdict = det['verdict']
        self.last_inspect = time.time()
        types = sorted({d['type'] for d in det['defects']})
        ev = {'seq': seq, 'name': name, 'time': stamp.strftime('%H:%M:%S'), 'verdict': verdict, 'types': types,
              'n': len(det['defects']), 'max_conf': max((d['conf'] for d in det['defects']), default=0.0),
              'capture': f'/capture/{name}.jpg', 'report': 'none' if verdict == 'normal' else 'queued',
              'domain': domain, 'route': route['rule'] if route else None}
        with self.lock:
            ev['gt'] = self.compare(fidx, x0, y0, det)
            if ev['gt']:
                self._log_eval(ev)
            self.counts[verdict] += 1
            self.events.appendleft(ev)
            self.flash, self.flash_color = 10, COLOR[verdict]
            self.boards.append({'seq': seq, 'verdict': verdict, 'cx': seg['cx'], 'off': x0 - seg['cx'], 'y0': y0,
                                'w': sw, 'domain': domain,
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

    # ── 기록 에이전트 (뒤에서 한 건씩): 판정·결함·지식 → 대장 '확인 대기' ──
    # 기본은 Qwen 을 부르지 않고 기록만 한다 (한 건에 0.1초 남짓 → 기판이 2초마다 와도 밀리지 않음).
    # 보고서 문장은 작업자가 대장에서 그 기록을 열 때 작성한다 (ui.open_record). --write-now 면 예전처럼 바로 작성.
    def report_worker(self):
        while True:
            det, name, seq = self.reports.get()
            meta = {'part_no': f'LINE1-{seq:04d}', 'lot': f'L{datetime.now():%Y%m%d}-LIVE'}
            backlog = self.reports.qsize()
            use_llm = self.a.write_now and (backlog <= self.a.max_backlog
                                            or (det['verdict'] == 'reject' and backlog <= 2 * self.a.max_backlog))
            if use_llm:
                self._report_status(seq, 'writing')
                self.preview_every = 2          # Qwen 이 GPU 를 쓰는 동안 미리보기를 줄여 영상이 끊기지 않게
            try:
                try:
                    if not use_llm:
                        raise RuntimeError('log_only')
                    result = analyze_detected(det, name, lang=self.lang, meta=meta, source='live')
                    status = 'ready'
                except Exception as e:  # noqa: BLE001 — 기록만 (Ollama 가 꺼져 있어도 같은 길)
                    from agent.pipeline import format_meta, refresh
                    result = {'name': name, 'work': str(OUT / 'work' / name), 'part_info': format_meta(meta, self.lang),
                              'meta': meta, 'lang': self.lang, 'detection': det, 'source': 'live',
                              'text': {'summary': '', 'defects': [], 'causes': [], 'pending_ai': True}}
                    refresh(result, write=False)
                    status = 'logged' if str(e) == 'log_only' else 'no_llm'
                register_pending(result, xlsx=False)    # 엑셀 대장은 xlsx_worker 가 20초마다 모아서
                self.xlsx_dirty = True
                self._report_status(seq, status)
            except Exception as e:  # noqa: BLE001
                self._report_status(seq, 'error')
                print('report error:', e)
            finally:
                if self.reports.empty():
                    self.preview_every = 1

    # ── 미리 쓰기 (단계 1-4): 라인이 쉬는 동안(일시정지, 또는 몇 초간 새 제품 없음) 최근 기록의 보고서 문장을 미리 쓴다 ──
    # 작업자가 열 때 Qwen 을 기다리지 않게. 라인이 다시 돌면 다음 건부터 멈춘다 (쓰고 있던 한 건은 마저 쓴다).
    def idle(self, quiet=8):
        return self.reports.empty() and (self.paused or time.time() - self.last_inspect > quiet)

    def prefetch_worker(self, recent=6):
        while True:
            time.sleep(2)
            if not self.a.prefetch or not self.idle():
                continue
            todo = []
            for e in reversed(records.load(OUT)):     # 최신 기록부터
                if len(todo) >= recent:
                    break
                if not e['id'].startswith('live_') or e['status'] != 'pending' or e['id'] in self.prefetched:
                    continue
                try:
                    r = load_result(OUT / e['result_json'])
                except (OSError, ValueError, KeyError):
                    continue
                if needs_text(r):
                    todo.append((e, r))
            todo.sort(key=lambda x: x[1]['detection']['verdict'] != 'reject')   # 이상 먼저
            for e, r in todo:
                if not self.idle():
                    break
                self.prefetched.add(e['id'])
                self._report_status_by_name(e['id'], 'writing')
                try:
                    r['lang'] = self.lang
                    refresh(r, write=True)
                    register_pending(r, xlsx=False, when=e['일시'])   # 검사 시각은 그대로
                    self.xlsx_dirty = True
                    self._report_status_by_name(e['id'], 'ready')
                except Exception as ex:  # noqa: BLE001 — Ollama 가 꺼져 있으면 열 때 다시 시도
                    self._report_status_by_name(e['id'], 'logged')
                    print('prefetch error:', ex)

    def _report_status_by_name(self, name, status):
        with self.lock:
            for ev in self.events:
                if ev['name'] == name:
                    ev['report'] = status

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
        zx0, zx1 = (w - self.zone_w) // 2, (w + self.zone_w) // 2
        overlay = frame.copy()
        # 미리보기 박스: 아직 검사 전인 기판만 얇게 (화면 가장자리에 걸친 기판은 흐리게)
        inspected = [(b['cx'] + b['off'], b['cx'] + b['off'] + b['w']) for b in self.boards]
        for (x0, y0, x1, y1), name, conf in preview:
            mx = (x0 + x1) / 2
            if any(a <= mx <= b for a, b in inspected):
                continue
            seg = next((s for s in segs if s['x0'] <= mx <= s['x1']), None)
            faint = seg is None or seg['touch']              # 화면 가장자리에 걸친 기판은 흐리게
            col = (190, 190, 190) if faint else (255, 255, 0)  # 미리보기 = 하늘색 (판정 전)
            cv2.rectangle(overlay, (int(x0), int(y0)), (int(x1), int(y1)), col, 2, cv2.LINE_AA)
            label = f'{name} {conf:.2f}'
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
            label = f'#{b["seq"]} {STAMP[b["verdict"]]}' + (f' {SHORT[b["domain"]]}' if self.mixed else '')
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
        while True:
            if self.restart:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                t0, idx, self.restart = time.time(), 0, False
                with self.lock:
                    self.boards, self.prev_centers = [], []
            if self.paused and last is not None:
                self.publish(self.draw(last.copy(), self.segments(last), self.preview))
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
            self.publish(self.process(frame, idx))
            self.frame_no += 1

    def process(self, frame, idx):
        """프레임 하나: 제품 찾기 → 센싱 구역 판정 → 미리보기 → 그린 화면. idx = 영상의 몇 번째 프레임인지 (1부터).

        실시간 루프(run)와 오프라인 시뮬레이션 녹화(tools/record_line_sim.py)가 같이 쓴다.
        """
        ts = time.time()
        segs = self.segments(frame)
        # 기판 이동 → 판정 붙은 기판 위치 갱신
        zc = frame.shape[1] / 2
        with self.lock:
            kept = []
            for b in self.boards:
                # 혼합 라인: 왼쪽 끝에 걸쳐 잘린 제품은 보이는 부분의 가운데가 아니라 오른쪽 끝에서 위치를 잡는다 (박스가 밀리지 않게)
                est = [(s['x1'] - b['w'] - b['off'] if self.mixed and s['x0'] <= 0 else s['cx']) for s in segs]
                m = [c for c in est if -40 <= b['cx'] - c <= 120]
                if m:
                    b['cx'] = min(m, key=lambda c: b['cx'] - c)
                    kept.append(b)
            self.boards = kept
        # 센싱: 기판 중심이 화면 가운데를 지나는 순간 한 번
        for s in segs:
            if s['touch'] or s['x1'] - s['x0'] < self.min_w:
                continue
            prev = [p for p in self.prev_centers if 0 <= p - s['cx'] <= 120]
            if prev and min(prev) > zc >= s['cx']:
                self.inspect(frame, s, idx - 1 if self.a.camera is None else None)
        self.prev_centers = [s['cx'] for s in segs]
        # 미리보기 (화면 전체, 원래 크기로 · 혼합 라인은 다음에 센싱할 제품 하나만)
        self.preview_age += 1
        if self.preview_age >= self.preview_every:
            self.preview_age = 0
            if self.mixed:
                self.preview = self.preview_next(frame, segs)
            else:
                r = self.model.predict(frame, imgsz=self.preview_imgsz, conf=self.conf, verbose=False)[0]
                self.preview = [(b.tolist(), self.names[int(c)], float(p))
                                for b, c, p in zip(r.boxes.xyxy, r.boxes.cls, r.boxes.conf)]
        self.infer_ms = 0.8 * self.infer_ms + 0.2 * (time.time() - ts) * 1000
        if self.flash > 0:
            self.flash -= 1
        self.tick.append(time.time())
        if len(self.tick) > 1:
            self.fps = (len(self.tick) - 1) / (self.tick[-1] - self.tick[0])
        return self.draw(frame, segs, self.preview)

    def preview_next(self, frame, segs):
        """혼합 라인 미리보기: 화면 전체에 세 모델을 돌리면 GPU 가 밀리므로, 아직 판정 전이고 화면 안에 다 들어온 제품 중
        센싱 구역에 가장 가까운 하나만 분배 에이전트로 종류를 정해 그 모델 하나로 본다."""
        zc = frame.shape[1] / 2
        done = [(b['cx'] + b['off'], b['cx'] + b['off'] + b['w']) for b in self.boards]
        cand = [s for s in segs if not s['touch'] and s['x1'] - s['x0'] >= self.min_w and s['cx'] >= zc - 40
                and not any(a <= s['cx'] <= b for a, b in done)]
        if not cand:
            return []
        s = min(cand, key=lambda s: s['cx'])
        dom = self.route(frame, s, step=4)['domain']
        x0, x1, y0, y1 = int(s['x0']), int(s['x1']), int(s['y0']), int(s['y1'])
        model = self.models[dom]
        r = model.predict(frame[y0:y1, x0:x1], imgsz=MODELS[dom][1], conf=thresholds(dom)['conf_review'],
                          verbose=False)[0]
        return [([bx0 + x0, by0 + y0, bx1 + x0, by1 + y0], model.names[int(c)], float(p))
                for (bx0, by0, bx1, by1), c, p in zip(r.boxes.xyxy.tolist(), r.boxes.cls, r.boxes.conf)]

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
                'route_acc': round(e['routed_ok'] / e['boards'], 4) if self.mixed and e['boards'] else None,
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
    ap.add_argument('--line', choices=['pcb', 'phone', 'metal', 'mixed'], default=None,
                    help='라인 이름 → videos/<line>_conveyor.mp4 를 입력으로 (--source 대신)')
    ap.add_argument('--domain', choices=['pcb', 'msdd', 'mobile'], default=None,
                    help='검사 모델 (기본: 영상 json 의 domain, 없으면 pcb)')
    ap.add_argument('--board', type=int, default=640, help='제품(센싱 구역) 크기 px — 영상 json 에 있으면 그 값을 쓴다')
    ap.add_argument('--preview-imgsz', type=int, default=None,
                    help='미리보기 추론 크기 (기본: PCB·금속 1280 = 화면 원래 크기, 액정 640 = 제품이 학습 축척)')
    ap.add_argument('--lang', default='ko', choices=['ko', 'vi', 'en'])
    ap.add_argument('--no-prefetch', dest='prefetch', action='store_false',
                    help='라인이 쉬는 동안 최근 기록의 보고서 문장을 미리 쓰지 않는다')
    ap.add_argument('--write-now', action='store_true', help='기록할 때 바로 Qwen 보고서 문장까지 작성 (기본: 열 때 작성)')
    ap.add_argument('--max-backlog', type=int, default=2, help='--write-now 일 때, 대기가 이보다 많으면 문장 없이 기록')
    ap.add_argument('--no-loop', dest='loop', action='store_false')
    a = ap.parse_args()
    if a.line:
        a.source = str(ROOT / f'videos/{a.line}_conveyor.mp4')
    LINE = Line(a)
    threading.Thread(target=LINE.report_worker, daemon=True).start()
    threading.Thread(target=LINE.xlsx_worker, daemon=True).start()
    threading.Thread(target=LINE.prefetch_worker, daemon=True).start()
    threading.Thread(target=LINE.run, daemon=True).start()
    srv = ThreadingHTTPServer(('0.0.0.0', a.port), Handler)
    srv.daemon_threads = True
    print(f'live server: http://localhost:{a.port}/  (stream /stream.mjpg, state /state)')
    srv.serve_forever()


if __name__ == '__main__':
    main()
