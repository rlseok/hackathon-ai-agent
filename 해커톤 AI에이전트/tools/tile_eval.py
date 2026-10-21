"""타일링 검증 (mobile · pcb · msdd): 테스트 사진 여러 장을 이어 붙여 '큰 사진' 을 만들고,
정답 라벨(GT)과 비교해 ① 통째로 축소 추론  ② 타일링 추론  의 정밀도·재현율·F1 을 잰다.

이어 붙인 큰 사진은 결함 크기가 학습 사진과 같아서 (= 현장에서 고해상도로 찍은 큰 사진을 흉내) 타일링이 올바르게 동작하는지 볼 수 있다.
사용: python tools/tile_eval.py --domain mobile --grid 2 [--n 8]
"""
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent.detect import detect  # noqa: E402

DATA = {'mobile': ROOT.parent / 'data/mobile_surface/data.yaml',
        'pcb': ROOT.parent / 'data/huggingface/pcb-defect-v2/data.yaml',
        'msdd': ROOT.parent / 'data/huggingface/metal-surface-defect-v1/data.yaml'}


def test_dirs(domain):
    cfg = yaml.safe_load(DATA[domain].read_text(encoding='utf-8'))
    root = Path(cfg.get('path', DATA[domain].parent))
    if not root.is_absolute():
        root = (DATA[domain].parent / root).resolve()
    img_dir = (root / cfg['test']).resolve()
    lab_dir = Path(str(img_dir).replace('/images', '/labels'))
    return img_dir, lab_dir, cfg['names']


def read_gt(label_file, w, h, names):
    boxes = []
    if not label_file.exists():
        return boxes
    for line in label_file.read_text().splitlines():
        p = line.split()
        if len(p) < 5:
            continue
        c, v = int(p[0]), list(map(float, p[1:]))
        if len(v) == 4:
            cx, cy, bw, bh = v
            box = [(cx - bw / 2) * w, (cy - bh / 2) * h, (cx + bw / 2) * w, (cy + bh / 2) * h]
        else:
            xs, ys = np.array(v[0::2]) * w, np.array(v[1::2]) * h
            box = [xs.min(), ys.min(), xs.max(), ys.max()]
        boxes.append((names[c] if isinstance(names, list) else names[c], box))
    return boxes


def iou(a, b):
    ix, iy = max(0, min(a[2], b[2]) - max(a[0], b[0])), max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    return inter / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter + 1e-9)


def score(gt, preds, th=0.5):
    used, tp = set(), 0
    for p in sorted(preds, key=lambda d: -d['conf']):
        best = max(((iou(p['box_px'], g[1]), i) for i, g in enumerate(gt) if i not in used and g[0].lower() == p['type'].lower()),
                   default=(0, -1))
        if best[0] >= th:
            used.add(best[1])
            tp += 1
    return tp, len(preds) - tp, len(gt) - tp      # TP, FP, FN


def f1(tp, fp, fn):
    p, r = tp / (tp + fp + 1e-9), tp / (tp + fn + 1e-9)
    return p, r, 2 * p * r / (p + r + 1e-9)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--domain', required=True, choices=list(DATA))
    ap.add_argument('--grid', type=int, default=3)
    ap.add_argument('--n', type=int, default=8, help='이어 붙인 큰 사진 개수')
    a = ap.parse_args()
    img_dir, lab_dir, names = test_dirs(a.domain)
    imgs = sorted(p for p in img_dir.iterdir() if p.suffix.lower() in {'.jpg', '.jpeg', '.png'})
    g, per = a.grid, a.grid * a.grid
    tot = {'resize': np.zeros(3, int), 'tile': np.zeros(3, int)}
    tmp = ROOT / 'outputs/tile_eval'
    tmp.mkdir(parents=True, exist_ok=True)
    for k in range(min(a.n, len(imgs) // per)):
        group = imgs[k * per:(k + 1) * per]
        tiles = [cv2.imread(str(p)) for p in group]
        th_, tw_ = tiles[0].shape[:2]
        tiles = [cv2.resize(t, (tw_, th_)) for t in tiles]
        big = np.vstack([np.hstack(tiles[r * g:(r + 1) * g]) for r in range(g)])
        gt = []
        for i, p in enumerate(group):
            ox, oy = (i % g) * tw_, (i // g) * th_
            for cls, (x0, y0, x1, y1) in read_gt(lab_dir / f'{p.stem}.txt', tw_, th_, names):
                gt.append((cls, [x0 + ox, y0 + oy, x1 + ox, y1 + oy]))
        path = tmp / f'{a.domain}_mosaic{g}_{k}.jpg'
        cv2.imwrite(str(path), big, [cv2.IMWRITE_JPEG_QUALITY, 98])
        for mode, flag in (('resize', False), ('tile', True)):
            dets = detect(path, a.domain, tile=flag)['defects']
            tot[mode] += score(gt, dets)
    print(f'[{a.domain}] 큰 사진 {a.n}장 ({big.shape[1]}×{big.shape[0]}), 정답 {tot["tile"][0] + tot["tile"][2]}개 (IoU≥0.5, 신뢰도 기준은 judgment.conf_review)')
    for mode, v in tot.items():
        p, r, f = f1(*v)
        print(f'  {mode:7s} TP {v[0]:3d} FP {v[1]:3d} FN {v[2]:3d}  정밀도 {p:.3f} 재현율 {r:.3f} F1 {f:.3f}')


if __name__ == '__main__':
    main()
