"""실시간 검사 한 바퀴의 대조 기록(outputs/live/eval_*.csv)에서 '잘 된 결과'를 골라 샘플 자료로 정리한다.

잘 된 결과 = 판정이 정답과 맞고(결함 제품은 이상/의심, 정상 제품은 정상), 결함도 모두 맞힘(오탐·놓침 0).
케이스(유형)별로 최대 --per 장: 캡처 원본 | 검출 표시 를 나란히 붙인 사진, 케이스별 모아보기, AI 보고서 문장(있으면), 요약 md.

실행: .venv\\Scripts\\python tools/collect_live_samples.py [--csv outputs/live/eval_….csv] [--video videos/phone_conveyor.mp4]
                                                          [--out results/mobile/live_samples] [--per 4]
"""
import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT_ROOT = ROOT / 'outputs'
STAMP = {'reject': 'NG', 'review': 'HOLD', 'normal': 'OK'}
COLOR = {'reject': (40, 40, 225), 'review': (0, 150, 255), 'normal': (70, 175, 70)}


def panel(raw, marked, title, verdict):
    h = 360
    a = cv2.resize(raw, (int(raw.shape[1] * h / raw.shape[0]), h))
    b = cv2.resize(marked, (int(marked.shape[1] * h / marked.shape[0]), h))
    body = np.hstack([a, np.full((h, 8, 3), 30, np.uint8), b])
    bar = np.full((44, body.shape[1], 3), 24, np.uint8)
    cv2.rectangle(bar, (0, 0), (110, 44), COLOR[verdict], -1)
    cv2.putText(bar, STAMP[verdict], (14, 31), cv2.FONT_HERSHEY_DUPLEX, 0.95, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(bar, title, (124, 29), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (235, 235, 235), 1, cv2.LINE_AA)
    return np.vstack([bar, body])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', default=None, help='대조 기록 (기본: 가장 최근 outputs/live/eval_*.csv)')
    ap.add_argument('--video', default=str(ROOT / 'videos/phone_conveyor.mp4'))
    ap.add_argument('--out', default=str(ROOT / 'results/mobile/live_samples'))
    ap.add_argument('--per', type=int, default=4)
    a = ap.parse_args()
    csv_path = Path(a.csv) if a.csv else sorted((OUT_ROOT / 'live').glob('eval_*.csv'))[-1]
    rows = list(csv.DictReader(open(csv_path, encoding='utf-8-sig')))
    m = json.loads(Path(a.video).with_suffix('.json').read_text(encoding='utf-8'))
    cases = {b['index']: b['case'] for b in m['boards']}
    sources = {b['index']: b['source'] for b in m['boards']}     # 같은 사진이 영상에 여러 번 나와도 샘플은 한 번
    out = Path(a.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    good = [r for r in rows if r['board_ok'] == '1' and r['fp'] == '0' and r['fn'] == '0']
    seen, by_case = set(), {}
    for r in good:                                   # 영상이 반복돼도 같은 제품은 한 번만
        bi = int(r['video_board'])
        if sources[bi] in seen:
            continue
        seen.add(sources[bi])
        by_case.setdefault(cases[bi], []).append(r)

    lines = [f'# 실시간 검사 샘플 — {m["video"]}', '',
             f'- 대조 기록: `{csv_path.name}` ({len(rows)}건 판정)',
             f'- 잘 된 결과 (판정 일치 + 결함 오탐·놓침 0): {len(good)}건 / 서로 다른 사진 {len(seen)}장', '',
             '| 케이스 | 샘플 | 순서 | 판정 | 검출 유형 | AI 요약 |', '|---|---|---|---|---|---|']
    for case in sorted(by_case):
        picks = by_case[case][:a.per]
        d = out / case
        d.mkdir()
        tiles = []
        for k, r in enumerate(picks, 1):
            name = r['capture']
            raw = cv2.imread(str(OUT_ROOT / 'live/captures' / f'{name}.jpg'))
            marked = cv2.imread(str(OUT_ROOT / 'work' / name / f'{name}_marked.jpg'))
            if raw is None or marked is None:
                continue
            title = f'#{r["seq"]}  {case}  ->  {r["pred_types"] or "no defect"}  (truth: {r["gt_types"] or "normal"})'
            pn = panel(raw, marked, title, r['verdict'])
            fn = f'{k:02d}_{name}.jpg'
            cv2.imwrite(str(d / fn), pn, [cv2.IMWRITE_JPEG_QUALITY, 90])
            tiles.append(pn)
            summary = ''
            res = OUT_ROOT / 'work' / name / f'{name}_result.json'
            if res.exists():                         # 보고 에이전트가 쓴 문장 (이상·의심만)
                tx = json.loads(res.read_text(encoding='utf-8')).get('text', {})
                summary = (tx.get('summary') or '').replace('|', '/')
                (d / f'{k:02d}_{name}_report_text.json').write_text(json.dumps(tx, ensure_ascii=False, indent=1), encoding='utf-8')
            lines.append(f'| {case} | [{fn}]({case}/{fn}) | #{r["seq"]} | {STAMP[r["verdict"]]} | {r["pred_types"] or "-"} | {summary[:80]} |')
        if tiles:
            wmax = max(t.shape[1] for t in tiles)
            tiles = [cv2.copyMakeBorder(t, 0, 6, 0, wmax - t.shape[1], cv2.BORDER_CONSTANT, value=(18, 18, 18)) for t in tiles]
            cv2.imwrite(str(d / 'overview.jpg'), np.vstack(tiles), [cv2.IMWRITE_JPEG_QUALITY, 85])
    (out / 'README.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'{len(good)} good results, {len(seen)} products → {out}')
    for c, v in sorted(by_case.items()):
        print(f'  {c}: {len(v)} good, saved {min(len(v), a.per)}')


if __name__ == '__main__':
    main()
