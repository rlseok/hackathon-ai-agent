"""YOLO 라벨을 이미지 위에 그려 클래스별 샘플 격자 이미지를 만든다 (라벨 육안 검수용).

사용: python label_preview.py <split 폴더(images, labels 포함)> <data.yaml> <출력 폴더> [--per-class 12] [--seed 0]
"""
import argparse
import random
from pathlib import Path

import cv2
import numpy as np
import yaml

COLORS = [(0, 0, 255), (0, 200, 255), (0, 255, 0), (255, 200, 0),
          (255, 0, 0), (255, 0, 255), (128, 0, 255), (0, 128, 255)]


def imread(p):
    return cv2.imdecode(np.fromfile(str(p), np.uint8), cv2.IMREAD_COLOR)


def imwrite(p, img):
    cv2.imencode(p.suffix, img)[1].tofile(str(p))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('split', type=Path)
    ap.add_argument('yaml', type=Path)
    ap.add_argument('out', type=Path)
    ap.add_argument('--per-class', type=int, default=12)
    ap.add_argument('--seed', type=int, default=0)
    args = ap.parse_args()

    names = yaml.safe_load(args.yaml.read_text(encoding='utf-8'))['names']
    by_cls = {i: [] for i in range(len(names))}
    for lbl in sorted((args.split / 'labels').glob('*.txt')):
        cls = {int(l.split()[0]) for l in lbl.read_text().splitlines() if l.strip()}
        for c in cls:
            by_cls[c].append(lbl)

    args.out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    tile = 320
    for c, lbls in by_cls.items():
        picks = rng.sample(lbls, min(args.per_class, len(lbls)))
        tiles = []
        for lbl in picks:
            img_p = next((args.split / 'images').glob(lbl.stem + '.*'))
            img = imread(img_p)
            h, w = img.shape[:2]
            for line in lbl.read_text().splitlines():
                p = line.split()
                if not p:
                    continue
                k, (x, y, bw, bh) = int(p[0]), map(float, p[1:5])
                x0, y0 = int((x - bw / 2) * w), int((y - bh / 2) * h)
                x1, y1 = int((x + bw / 2) * w), int((y + bh / 2) * h)
                # 대상 클래스는 굵게, 나머지는 얇게
                cv2.rectangle(img, (x0, y0), (x1, y1), COLORS[k % 8], 3 if k == c else 1)
            img = cv2.resize(img, (tile, tile))
            cv2.putText(img, lbl.stem[:40], (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            tiles.append(img)
        while len(tiles) % 4:
            tiles.append(np.zeros((tile, tile, 3), np.uint8))
        rows = [np.hstack(tiles[i:i + 4]) for i in range(0, len(tiles), 4)]
        grid = np.vstack(rows)
        imwrite(args.out / f'{c}_{names[c]}.jpg', grid)
        print(f'{c} {names[c]}: {len(lbls)} images -> {len(picks)} sampled')


if __name__ == '__main__':
    main()
