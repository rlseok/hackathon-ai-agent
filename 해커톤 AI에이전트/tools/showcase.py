"""test 세트에서 '잘 맞힌' 이미지를 케이스(결함 유형)별로 골라 정리한다.

잘 맞힘의 기준 (신뢰도 기준 conf 이상 예측만 사용):
- 정답 결함이 모두 같은 유형의 예측과 IoU>=0.5 로 매칭됨 (놓침 없음)
- 매칭되지 않은 예측 없음 (오탐 없음)
- 순위: 매칭된 예측 신뢰도의 평균이 높은 순
정답 라벨이 비어 있고 예측도 없는 이미지는 '정상' 케이스로 정리한다 (최고 신뢰도가 낮은 순).

출력: <out>/<번호_케이스>/NN_<이미지>.jpg (왼쪽 정답, 오른쪽 예측), <out>/<케이스>/overview.jpg, <out>/summary.csv

사용: python showcase.py <best.pt> <data.yaml> <out> [--split test] [--conf 0.25] [--top 10] [--imgsz 640]
"""
import argparse
import csv
from pathlib import Path

import cv2
import numpy as np
import yaml
from ultralytics import YOLO

GT_COLOR = (0, 220, 0)


def imread(p):
    return cv2.imdecode(np.fromfile(str(p), np.uint8), cv2.IMREAD_COLOR)


def imwrite(p, img):
    cv2.imencode('.jpg', img)[1].tofile(str(p))


def read_gt(lbl, w, h):
    """[(cls, xyxy, polygon or None)] 픽셀 좌표."""
    out = []
    if not lbl.exists():
        return out
    for line in lbl.read_text().splitlines():
        p = line.split()
        if not p:
            continue
        c, v = int(p[0]), np.array(list(map(float, p[1:])))
        if len(v) == 4:
            x, y, bw, bh = v
            box = np.array([(x - bw / 2) * w, (y - bh / 2) * h, (x + bw / 2) * w, (y + bh / 2) * h])
            out.append((c, box, None))
        else:
            pts = v.reshape(-1, 2) * [w, h]
            box = np.array([*pts.min(0), *pts.max(0)])
            out.append((c, box, pts.astype(np.int32)))
    return out


def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0


def match(gt, pred_cls, pred_box, pred_conf):
    """그리디 매칭. (모두 매칭?, 오탐 수, 매칭된 신뢰도 목록)"""
    used, confs = set(), []
    order = np.argsort(-pred_conf)
    for c, box, _ in gt:
        best, bi = 0.5, None
        for j in order:
            if j in used or pred_cls[j] != c:
                continue
            v = iou(box, pred_box[j])
            if v >= best:
                best, bi = v, j
        if bi is None:
            return False, None, confs
        used.add(bi)
        confs.append(float(pred_conf[bi]))
    return True, len(pred_cls) - len(used), confs


def draw_gt(img, gt, names):
    img = img.copy()
    for c, box, poly in gt:
        if poly is not None:
            cv2.polylines(img, [poly], True, GT_COLOR, 2)
        else:
            cv2.rectangle(img, tuple(box[:2].astype(int)), tuple(box[2:].astype(int)), GT_COLOR, 2)
        cv2.putText(img, names[c], (int(box[0]), max(12, int(box[1]) - 3)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, GT_COLOR, 1)
    return img


def panel(gt_img, pred_img, title):
    h = 480
    a = cv2.resize(gt_img, (int(gt_img.shape[1] * h / gt_img.shape[0]), h))
    b = cv2.resize(pred_img, (a.shape[1], h))
    bar = np.full((28, a.shape[1] * 2 + 6, 3), 30, np.uint8)
    cv2.putText(bar, f'GT (label)  |  Prediction   {title}', (6, 19),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    return np.vstack([bar, np.hstack([a, np.full((h, 6, 3), 255, np.uint8), b])])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('model', type=Path)
    ap.add_argument('data', type=Path)
    ap.add_argument('out', type=Path)
    ap.add_argument('--split', default='test')
    ap.add_argument('--conf', type=float, default=0.25)
    ap.add_argument('--top', type=int, default=10)
    ap.add_argument('--imgsz', type=int, default=640)
    args = ap.parse_args()

    cfg = yaml.safe_load(args.data.read_text(encoding='utf-8'))
    names = cfg['names']
    root = Path(cfg['path'])
    img_dir = root / cfg[args.split if args.split != 'valid' else 'val']
    lbl_dir = Path(str(img_dir).replace('images', 'labels'))
    model = YOLO(str(args.model))

    imgs = sorted(img_dir.iterdir())
    rows, results = [], {}
    for i in range(0, len(imgs), 16):
        batch = imgs[i:i + 16]
        for p, r in zip(batch, model.predict([str(x) for x in batch], imgsz=args.imgsz,
                                             conf=args.conf, verbose=False)):
            h, w = r.orig_shape
            gt = read_gt(lbl_dir / (p.stem + '.txt'), w, h)
            pc = r.boxes.cls.cpu().numpy().astype(int)
            pb = r.boxes.xyxy.cpu().numpy()
            pf = r.boxes.conf.cpu().numpy()
            ok, fp, confs = match(gt, pc, pb, pf)
            perfect = ok and fp == 0
            score = float(np.mean(confs)) if confs else (1 - float(pf.max()) if len(pf) else 1.0)
            results[p] = (r, gt)
            rows.append(dict(image=p.name, gt=len(gt), pred=len(pc), perfect=perfect,
                             classes=sorted({c for c, _, _ in gt}), score=round(score, 4)))

    # 케이스 구성: 결함 유형별 + 정상
    cases = [(f'{i:02d}_{n.replace(" ", "")}', lambda r, i=i: i in r['classes']) for i, n in enumerate(names)]
    cases.append((f'{len(names):02d}_Normal', lambda r: r['gt'] == 0))
    args.out.mkdir(parents=True, exist_ok=True)
    summary = []
    for case, cond in cases:
        cand = [r for r in rows if r['perfect'] and cond(r)]
        total = sum(1 for r in rows if cond(r))
        cand.sort(key=lambda r: -r['score'])
        picks = cand[:args.top]
        summary.append((case, total, len(cand), picks))
        if not picks:
            continue
        d = args.out / case
        d.mkdir(exist_ok=True)
        thumbs = []
        for k, row in enumerate(picks, 1):
            p = img_dir / row['image']
            r, gt = results[p]
            img = imread(p)
            title = f'#{k}  score {row["score"]:.2f}  defects {row["gt"]}'
            pn = panel(draw_gt(img, gt, names), r.plot(), title)
            imwrite(d / f'{k:02d}_{p.stem[:60]}.jpg', pn)
            thumbs.append(cv2.resize(pn, (pn.shape[1] // 2, pn.shape[0] // 2)))
        cols = 2
        while len(thumbs) % cols:
            thumbs.append(np.zeros_like(thumbs[0]))
        imwrite(d / 'overview.jpg', np.vstack([np.hstack(thumbs[i:i + cols]) for i in range(0, len(thumbs), cols)]))

    with open(args.out / 'summary.csv', 'w', newline='', encoding='utf-8-sig') as f:
        wr = csv.writer(f)
        wr.writerow(['case', 'images_in_case', 'perfect_images', 'perfect_rate', 'rank', 'image', 'score', 'n_defects'])
        for case, total, n_perfect, picks in summary:
            rate = f'{n_perfect / total:.1%}' if total else '-'
            if not picks:
                wr.writerow([case, total, n_perfect, rate, '', '', '', ''])
            for k, row in enumerate(picks, 1):
                wr.writerow([case, total, n_perfect, rate, k, row['image'], row['score'], row['gt']])
    for case, total, n_perfect, picks in summary:
        print(f'{case:16s} images={total:4d} perfect={n_perfect:4d} ({n_perfect / max(1, total):.0%}) picked={len(picks)}')


if __name__ == '__main__':
    main()
