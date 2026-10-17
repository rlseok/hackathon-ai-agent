"""판정 기준값(conf) 검증: 기준값별 오탐률·불량 검출률 표.

두 가지 입력:
  --normal <폴더...>   결함 없는 정상 사진 폴더 → 기준값별 '정상인데 불량/재검으로 판정된 사진 비율'
  --labeled <폴더...>  images/ + labels/ (YOLO 형식) 폴더 → 기준값별 사진 판정 정확도와 사진당 오탐 박스 수
                       (labels 가 비어 있는 사진은 정상 사진으로 함께 계산)

사용 예 (패키지 폴더에서):
  python tools/fp_eval.py --domain msdd --normal results/msdd/showcase/06_Normal/originals/images
  python tools/fp_eval.py --domain pcb --labeled results/pcb/showcase/*/originals
  python tools/fp_eval.py --domain pcb --labeled D:/pcb_v2/test       # 데스크톱 test 세트를 복사해 온 경우
현장 정상 사진을 받으면 --normal 로 돌려 knowledge/defect_taxonomy_<domain>.yaml 의 judgment 값을 정한다.
"""
import argparse
import glob
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent.detect import MODELS, _model, thresholds  # noqa: E402

THS = [0.10, 0.25, 0.40, 0.50, 0.60]
EXTS = {'.jpg', '.jpeg', '.png', '.bmp'}


def predict_all(paths, domain):
    """한 번만 낮은 기준(0.05)으로 추론해 두고 기준값별로 걸러 쓴다."""
    model, imgsz = _model(domain), MODELS[domain][1]
    out = []
    for p in paths:
        r = model.predict(str(p), imgsz=imgsz, conf=0.05, verbose=False)[0]
        h, w = r.orig_shape
        out.append([(model.names[int(c)], float(s), (b / np.array([w, h, w, h])).tolist())
                    for c, s, b in zip(r.boxes.cls, r.boxes.conf, r.boxes.xyxy.cpu().numpy())])
    return out, model.names


def read_labels(path, names):
    gt = []
    if path.exists():
        for line in path.read_text().split('\n'):
            v = line.split()
            if len(v) < 5:
                continue
            c, xy = int(v[0]), np.array(v[1:], float)
            if len(v) == 5:                  # 박스: cx cy w h
                cx, cy, bw, bh = xy
                box = [cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2]
            else:                            # 폴리곤 → 외접 박스
                p = xy.reshape(-1, 2)
                box = [*p.min(0), *p.max(0)]
            gt.append((names[c], box))
    return gt


def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    return inter / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter + 1e-9)


def count_fp(gt, preds, th_iou=0.5):
    """정답과 같은 유형·IoU≥0.5 로 매칭되지 않은 예측 수."""
    used = set()
    for t, g in gt:
        best = max(((iou(g, b), i) for i, (pt, _, b) in enumerate(preds) if pt == t and i not in used), default=(0, -1))
        if best[0] >= th_iou:
            used.add(best[1])
    return len(preds) - len(used), [preds[i][0] for i in range(len(preds)) if i not in used]


def images_in(dirs):
    paths = []
    for d in dirs:
        for g in glob.glob(d):
            g = Path(g)
            base = g / 'images' if (g / 'images').is_dir() else g
            paths += sorted(p for p in base.iterdir() if p.suffix.lower() in EXTS)
    return paths


def eval_normal(dirs, domain):
    paths = images_in(dirs)
    preds, _ = predict_all(paths, domain)
    print(f'정상 사진 {len(paths)}장 ({domain})')
    print(f'{"기준값":>6} {"오탐 사진":>9} {"오탐률":>7}  오탐 유형')
    for th in THS:
        hits = [[p for p in ps if p[1] >= th] for ps in preds]
        n = sum(bool(h) for h in hits)
        types = Counter(t for h in hits for t, _, _ in h)
        print(f'{th:6.2f} {n:5d}/{len(paths):<3d} {100 * n / max(len(paths), 1):6.1f}%  {dict(types.most_common(4))}')


def eval_labeled(dirs, domain):
    paths = images_in(dirs)
    preds, names = predict_all(paths, domain)
    gts = [read_labels(p.parents[1] / 'labels' / f'{p.stem}.txt', names) for p in paths]
    n_def = sum(bool(g) for g in gts)
    print(f'라벨 사진 {len(paths)}장 (결함 {n_def}, 정상 {len(paths) - n_def}) ({domain})')
    print(f'{"기준값":>6} {"불량 검출률":>10} {"정상 인식률":>10} {"사진 정확도":>10} {"사진당 오탐":>10}  오탐 유형')
    for th in THS:
        tp = tn = fp_boxes = 0
        fp_types = Counter()
        for g, ps in zip(gts, preds):
            ps = [p for p in ps if p[1] >= th]
            if g:
                tp += bool(ps)
            else:
                tn += not ps
            n, types = count_fp(g, ps)
            fp_boxes += n
            fp_types.update(types)
        n_ok = len(paths) - n_def
        rec = f'{100 * tp / n_def:.1f}%' if n_def else '-'
        spec = f'{100 * tn / n_ok:.1f}%' if n_ok else '-'
        print(f'{th:6.2f} {rec:>10} {spec:>10} {100 * (tp + tn) / len(paths):9.1f}% '
              f'{fp_boxes / len(paths):10.2f}  {dict(fp_types.most_common(4))}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--domain', default='pcb', choices=list(MODELS))
    ap.add_argument('--normal', nargs='+')
    ap.add_argument('--labeled', nargs='+')
    a = ap.parse_args()
    th = thresholds(a.domain)
    print(f'현재 기준: 재검 {th["conf_review"]} / 불량 {th["conf_reject"]}')
    if a.normal:
        eval_normal(a.normal, a.domain)
    if a.labeled:
        eval_labeled(a.labeled, a.domain)
    if not (a.normal or a.labeled):
        ap.print_help()
