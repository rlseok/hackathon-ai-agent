"""타일링 추론 검증: PCB 우수 사례 조각을 2×2·3×3·4×4 로 이어 붙인 큰 사진(1280~2560px)에서
   ① 조각별 추론 결과(기준)  ② 타일링 추론  ③ 통째로 640 축소 추론  을 비교한다.

사용: python tools/tile_check.py   (패키지 폴더에서)
"""
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent.detect import detect  # noqa: E402

OUT = ROOT / 'outputs/tile_check'


def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    return inter / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter + 1e-9)


def match(ref, pred, th=0.5):
    """같은 유형, IoU≥th 로 1:1 매칭 → (찾음, 놓침, 추가)."""
    used, hit = set(), 0
    for r in ref:
        best = max(((iou(r['box_px'], p['box_px']), i) for i, p in enumerate(pred)
                    if i not in used and p['type'] == r['type']), default=(0, -1))
        if best[0] >= th:
            used.add(best[1])
            hit += 1
    return hit, len(ref) - hit, len(pred) - len(used)


def main(grid=2, n_sets=3):
    OUT.mkdir(parents=True, exist_ok=True)
    imgs = sorted((ROOT / 'results/pcb/showcase').glob('*/originals/images/0[2-6]_*'))
    imgs = list({p.name.split('_', 1)[1]: p for p in imgs}.values())   # 케이스 간 중복 사진 제거
    n = grid * grid
    n_sets = min(n_sets, len(imgs) // n)
    sets = [imgs[i * n:(i + 1) * n] for i in range(n_sets)]
    tot = {'tile': np.zeros(3, int), 'resize': np.zeros(3, int)}
    for k, group in enumerate(sets):
        tiles = [cv2.imread(str(p)) for p in group]
        big = np.vstack([np.hstack(tiles[r * grid:(r + 1) * grid]) for r in range(grid)])
        big_path = OUT / f'mosaic{grid}x{grid}_{k}.jpg'
        cv2.imwrite(str(big_path), big, [cv2.IMWRITE_JPEG_QUALITY, 98])
        ref = []                                   # 조각별 결과를 큰 사진 좌표로
        for i, p in enumerate(group):
            ox, oy = 640 * (i % grid), 640 * (i // grid)
            for d in detect(p, 'pcb')['defects']:
                x0, y0, x1, y1 = d['box_px']
                ref.append({'type': d['type'], 'box_px': [x0 + ox, y0 + oy, x1 + ox, y1 + oy]})
        tiled = detect(big_path, 'pcb', OUT / 'tiled', tile=True)
        resized = detect(big_path, 'pcb', tile=False)
        for name, det in (('tile', tiled), ('resize', resized)):
            m = match(ref, det['defects'])
            tot[name] += m
            print(f'{big_path.stem} {name:6s} 기준 {len(ref):2d}개 → 찾음 {m[0]:2d}, 놓침 {m[1]:2d}, 추가 {m[2]:2d}'
                  + (f'  ({det["tiles"]}조각)' if name == 'tile' else ''))
    for name, (hit, miss, extra) in tot.items():
        print(f'합계 {grid}x{grid} {name:6s} 찾음 {hit}/{hit + miss} ({100 * hit / max(hit + miss, 1):.0f}%), 추가 {extra}')


if __name__ == '__main__':
    for g in (2, 3, 4):              # 1280 / 1920 / 2560 px
        main(g)
