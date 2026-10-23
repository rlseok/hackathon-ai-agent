"""실시간 라인 센싱 시뮬레이션 녹화 — 가상 컨베이어 영상을 한 프레임도 건너뛰지 않고 영상 서버와 같은 처리로 돌려
화면(미리보기 박스 · 센싱 구역 · 판정 도장)을 영상으로 저장하고, 정답과 비교한 정확도를 정리한다.

  videos/<line>_sensing_sim.mp4             녹화 영상 (영상 파일은 git 에 올리지 않는다)
  results/live_sim/<line>_boards.csv        제품별 정답 대조 (정답 종류·유형, 판정, 검출 유형, TP/FP/FN, 처리 시간)
  results/live_sim/summary.json             라인별 요약 (tools/live_sim_table.py 가 표로 만든다)

실시간 서버와 달리 시간에 맞춰 프레임을 건너뛰지 않으므로 모든 제품이 센싱 구역을 지난다. Qwen 보고서는 쓰지 않는다.
화면의 fps 는 처리 능력(1000 / 프레임당 처리 ms)이다 (녹화·인코딩 시간 제외).

실행: .venv\\Scripts\\python tools/record_line_sim.py --line pcb phone metal
"""
import argparse
import csv
import json
import shutil
import sys
import time
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from live import server  # noqa: E402

OUT_DIR = ROOT / 'results/live_sim'
LINE_NAME = {'pcb': 'PCB', 'phone': 'LCD (phone surface)', 'metal': 'Metal surface', 'mixed': 'Mixed'}


class SimLine(server.Line):
    def draw(self, frame, segs, preview):
        self.fps = 1000 / max(self.infer_ms, 1e-3)     # 처리 능력 (녹화 시간 제외)
        img = super().draw(frame, segs, preview)
        label = f'SIMULATION  ·  {LINE_NAME[self.line_key]} line'
        cv2.putText(img, label, (img.shape[1] - 470, img.shape[0] - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    (235, 235, 235), 1, cv2.LINE_AA)
        return img


def run(line, suffix=''):
    src = ROOT / f'videos/{line}_conveyor{suffix}.mp4'
    a = SimpleNamespace(source=str(src), camera=None, domain=None, board=640, preview_imgsz=None, lang='ko',
                        max_backlog=2, write_now=False, prefetch=False, loop=False)
    sim = SimLine(a)
    sim.line_key = line
    cap = cv2.VideoCapture(str(src))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    mp4 = ROOT / f'videos/{line}{suffix}_sensing_sim.mp4'
    writer = cv2.VideoWriter(str(mp4), cv2.VideoWriter_fourcc(*'avc1'), fps, (w, h))
    proc_ms, idx, t_start = [], 0, time.time()
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        idx += 1
        ts = time.perf_counter()
        img = sim.process(frame, idx)
        proc_ms.append((time.perf_counter() - ts) * 1000)
        writer.write(img)
        if idx % 600 == 0:
            print(f'  {line}: {idx}/{n_frames} frames, {sim.seq} inspected')
    cap.release()
    writer.release()

    # 제품별 대조: 영상 서버의 대조 기록(outputs/live/eval_*.csv)을 결과 폴더로 옮겨 둔다
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    if sim.eval_log and sim.eval_log.exists():
        with open(sim.eval_log, encoding='utf-8-sig') as f:
            rows = list(csv.DictReader(f))
        shutil.move(str(sim.eval_log), OUT_DIR / f'{line}{suffix}_boards.csv')
    e = sim._eval_summary()
    by_type = {}
    for r in rows:                                   # 정답 유형별 제품 판정 (결함 제품만, 유형 하나짜리 기준)
        key = r['gt_types'] or 'normal'
        t = by_type.setdefault(key, {'items': 0, 'correct': 0, 'verdicts': Counter()})
        t['items'] += 1
        t['correct'] += int(r['board_ok'])
        t['verdicts'][r['verdict']] += 1
    by_domain = {}
    for r in rows:                                   # 혼합 라인: 제품 종류별 분배·판정
        if 'gt_domain' not in r:
            break
        t = by_domain.setdefault(r['gt_domain'], {'items': 0, 'routed_ok': 0, 'correct': 0, 'rules': Counter()})
        t['items'] += 1
        t['routed_ok'] += int(r['domain'] == r['gt_domain'])
        t['correct'] += int(r['board_ok'])
        t['rules'][r['route_rule']] += 1
    proc_ms.sort()
    return {
        'line': line, 'name': LINE_NAME[line], 'domain': sim.domain, 'video': mp4.name,
        'frames': idx, 'video_seconds': round(idx / fps, 1), 'items_in_video': len(sim.gt['boards']),
        'inspected': sim.seq, 'unmatched': e['unmatched'],
        'verdicts': dict(sim.counts),
        'board_acc': e['board_acc'], 'correct': e['correct'], 'boards': e['boards'],
        'defect_caught': e['defect_caught'], 'defect_boards': e['defect_boards'],
        'normal_passed': e['normal_passed'], 'normal_boards': e['normal_boards'],
        'tp': e['tp'], 'fp': e['fp'], 'fn': e['fn'], 'precision': e['precision'], 'recall': e['recall'], 'f1': e['f1'],
        'proc_ms_mean': round(sum(proc_ms) / len(proc_ms), 1), 'proc_ms_p95': round(proc_ms[int(0.95 * len(proc_ms))], 1),
        'proc_fps': round(1000 / (sum(proc_ms) / len(proc_ms)), 1),
        'wall_seconds': round(time.time() - t_start, 1),
        'by_type': {k: {**v, 'verdicts': dict(v['verdicts'])} for k, v in sorted(by_type.items())},
        'route_acc': e['route_acc'], 'routed_ok': e['routed_ok'],
        'by_domain': {k: {**v, 'rules': dict(v['rules'])} for k, v in sorted(by_domain.items())},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--line', nargs='+', choices=['pcb', 'phone', 'metal', 'mixed'], default=['pcb', 'phone', 'metal'])
    ap.add_argument('--suffix', default='', help="다른 영상 세트: videos/<line>_conveyor<suffix>.mp4 → 결과 키 '<line><suffix>'")
    a = ap.parse_args()
    summary_path = OUT_DIR / 'summary.json'
    summary = json.loads(summary_path.read_text(encoding='utf-8')) if summary_path.exists() else {}
    for line in a.line:
        print(f'{line}: simulating …')
        s = run(line, a.suffix)
        summary[line + a.suffix] = s
        print(f'  {line}: {s["inspected"]} inspected, verdict accuracy {s["board_acc"]}, F1 {s["f1"]}, '
              f'{s["proc_ms_mean"]} ms/frame → {s["video"]}')
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
