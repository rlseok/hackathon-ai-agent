"""가상 컨베이어 영상의 정답(json)으로 실시간 검사 정확도를 잰다.

영상 서버와 같은 방식으로 기판이 센싱 구역 가운데 온 프레임을 640×640 으로 잘라 agent.detect.detect 로 검사하고,
영상 json 의 정답 라벨(종류·위치)과 비교한다.

- 기판 단위: 결함 기판을 이상/의심으로 잡았는지, 정상 기판을 정상으로 통과시켰는지
- 결함 단위: 예측 박스와 정답 박스가 같은 종류이고 IoU ≥ 0.5 이면 맞힘 → Precision / Recall / F1 (전체·종류별)

주의: 영상은 showcase(모델이 원본 사진에서 이미 다 맞힌 사진)로 만들었으므로, 여기 점수는 '모델 성능'이 아니라
'영상 → 센싱 → 판정' 과정이 원본 사진 검사와 같은 결과를 내는지를 보여준다. 모델 성능은 test 세트 수치(docs/03)를 쓴다.

실행: .venv\\Scripts\\python tools/eval_conveyor.py [--video videos/pcb_conveyor.mp4] [--out results/pcb/conveyor_eval]
"""
import argparse
import csv
import json
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent.detect import detect  # noqa: E402


def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    return inter / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter + 1e-9)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--video', default=str(ROOT / 'videos/pcb_conveyor.mp4'))
    ap.add_argument('--out', default=str(ROOT / 'results/pcb/conveyor_eval'))
    a = ap.parse_args()
    video = Path(a.video)
    m = json.loads(video.with_suffix('.json').read_text(encoding='utf-8'))
    size, speed, zx0 = m['board_px'], m['speed_px_per_frame'], m['sensing_zone'][0]
    cap = cv2.VideoCapture(str(video))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    rows = []
    tp, fp, fn = Counter(), Counter(), Counter()
    with tempfile.TemporaryDirectory() as tmp:
        for b in m['boards']:
            f = b['center_frame']
            cap.set(cv2.CAP_PROP_POS_FRAMES, f)
            ok, frame = cap.read()
            crop = frame[b['y']:b['y'] + size, zx0:zx0 + size]
            p = Path(tmp) / f'b{b["index"]:03d}.jpg'
            cv2.imwrite(str(p), crop, [cv2.IMWRITE_JPEG_QUALITY, 95])
            det = detect(p, 'pcb', tile=False)
            dx = round(b['x0'] - f * speed) - zx0             # 잘라낸 구역 안에서 기판이 밀린 만큼 (몇 px)
            gt = [(l['type'], [(l['cx'] - l['w'] / 2) * size + dx, (l['cy'] - l['h'] / 2) * size,
                               (l['cx'] + l['w'] / 2) * size + dx, (l['cy'] + l['h'] / 2) * size]) for l in b['labels']]
            preds = sorted(det['defects'], key=lambda d: -d['conf'])
            used = set()
            for d in preds:
                best, bj = 0.5, None
                for j, (t, g) in enumerate(gt):
                    if j not in used and t == d['type'] and iou(d['box_px'], g) >= best:
                        best, bj = iou(d['box_px'], g), j
                if bj is None:
                    fp[d['type']] += 1
                else:
                    used.add(bj)
                    tp[d['type']] += 1
            for j, (t, _) in enumerate(gt):
                if j not in used:
                    fn[t] += 1
            rows.append({'index': b['index'], 'kind': b['kind'], 'case': b['case'], 'verdict': det['verdict'],
                         'gt_defects': len(gt), 'pred_defects': len(preds), 'matched': len(used),
                         'missed': len(gt) - len(used), 'false_alarm': len(preds) - len(used),
                         'types': ' '.join(sorted({d['type'] for d in preds}))})

    # 기판 단위
    defect = [r for r in rows if r['kind'] == 'defect']
    normal = [r for r in rows if r['kind'] == 'normal']
    caught = sum(r['verdict'] != 'normal' for r in defect)
    passed = sum(r['verdict'] == 'normal' for r in normal)
    board = {'boards': len(rows), 'defect_boards': len(defect), 'normal_boards': len(normal),
             'defect_caught': caught, 'normal_passed': passed,
             'board_accuracy': round((caught + passed) / len(rows), 4),
             'defect_board_recall': round(caught / len(defect), 4) if defect else None,
             'normal_false_alarm_rate': round(1 - passed / len(normal), 4) if normal else None,
             'verdicts_on_defect_boards': dict(Counter(r['verdict'] for r in defect)),
             'verdicts_on_normal_boards': dict(Counter(r['verdict'] for r in normal))}

    # 결함 단위
    def prf(t, f_, n):
        p = t / (t + f_) if t + f_ else 0.0
        r = t / (t + n) if t + n else 0.0
        return round(p, 4), round(r, 4), round(2 * p * r / (p + r), 4) if p + r else 0.0
    per_class = {}
    for c in sorted(set(tp) | set(fp) | set(fn)):
        p, r, f1 = prf(tp[c], fp[c], fn[c])
        per_class[c] = {'tp': tp[c], 'fp': fp[c], 'fn': fn[c], 'precision': p, 'recall': r, 'f1': f1}
    P, R, F = prf(sum(tp.values()), sum(fp.values()), sum(fn.values()))
    defect_level = {'tp': sum(tp.values()), 'fp': sum(fp.values()), 'fn': sum(fn.values()),
                    'precision': P, 'recall': R, 'f1': F, 'per_class': per_class}

    summary = {'video': video.name, 'iou': 0.5, 'board_level': board, 'defect_level': defect_level}
    (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding='utf-8')
    with open(out / 'boards.csv', 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
