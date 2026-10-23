"""가상 컨베이어 영상 (금속 라인): 금속 부품 표면 사진을 컨베이어 위로 흘려보내는 '카메라' 영상을 만든다.

- 사진: results/msdd/showcase 의 원본(모델이 정답을 모두 맞힌 사진, 유형별 최대 10장) + Normal 케이스(진짜 정상 사진).
  산화(Oxidation)는 완벽히 맞힌 사진이 없어 빠진다. 정상 사진은 낮은 기준·압축 후에도 검출이 없는 것만 쓴다.
- 크기: 원본 512×512 그대로 (모델 학습 크기). 화면 가운데 512×512 센싱 구역에서 잘라 바로 검사한다.
- 벨트: 사진 배경이 검정이라 밝은 회색 벨트. 영상 서버는 '벨트 색과 다른 영역'으로 제품을 찾는다.

출력: videos/metal_conveyor.mp4, videos/metal_conveyor.json (액정 영상 json 과 같은 형식)
실행: .venv\\Scripts\\python tools/make_metal_video.py [--speed 14] [--seed 7] [--repeat 1]
"""
import argparse
import json
import random
import sys
from pathlib import Path

import cv2
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'results/msdd/showcase'
OUT = ROOT / 'videos'
MODEL = ROOT / 'models/msdd_v1_yolo11s_seg.pt'
NAMES = yaml.safe_load((ROOT / 'models/msdd_v1_data.yaml').read_text(encoding='utf-8'))['names']

W, H, FPS = 1280, 720, 30
BW = BH = 512
IMGSZ = 512
GAP = 160
LEAD = 40
BELT_TOP, BELT_BOTTOM = 26, H - 26
BELT = (128, 134, 140)       # 밝은 회색 (BGR) — 검정 배경의 금속 사진과 확실히 구분
SEAM = (138, 144, 150)
CONF, NORMAL_CONF = 0.25, 0.10


def read_labels(path):
    out = []
    if path.exists():
        for line in path.read_text().splitlines():
            v = line.split()
            if len(v) >= 7:
                xs, ys = np.array(v[1::2], float), np.array(v[2::2], float)
                out.append((NAMES[int(v[0])], (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2,
                            xs.max() - xs.min(), ys.max() - ys.min()))
    return out


def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    return inter / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter + 1e-9)


def perfect(r, labels):
    gt = [(t, [(cx - w / 2) * BW, (cy - h / 2) * BH, (cx + w / 2) * BW, (cy + h / 2) * BH]) for t, cx, cy, w, h in labels]
    used = set()
    for b, c in zip(r.boxes.xyxy.tolist(), r.boxes.cls.tolist()):
        hit = [(iou(b, g), j) for j, (t, g) in enumerate(gt) if j not in used and t == NAMES[int(c)]]
        best = max(hit, default=(0, None))
        if best[0] < 0.5:
            return False
        used.add(best[1])
    return len(used) == len(gt)


def belt_background():
    bg = np.full((H, W, 3), BELT, np.uint8)
    for y0, y1 in ((0, BELT_TOP), (BELT_BOTTOM, H)):
        grad = np.linspace(170, 110, y1 - y0).astype(np.uint8)
        bg[y0:y1] = np.repeat(grad[:, None, None], W, 1).repeat(3, 2)
    for y in (BELT_TOP, BELT_BOTTOM - 1):
        bg[y] = (60, 60, 64)
    yy, xx = np.mgrid[0:H, 0:W]
    d = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2
    return bg, (1.0 - 0.08 * np.clip(d, 0, 1.5))[..., None]


def paste(frame, img, x, y):
    h, w = img.shape[:2]
    for dx, dy, im, alpha in ((10, 10, None, 0.35), (0, 0, img, 1.0)):
        x0, y0 = x + dx, y + dy
        fx0, fx1, fy0, fy1 = max(x0, 0), min(x0 + w, W), max(y0, 0), min(y0 + h, H)
        if fx0 >= fx1 or fy0 >= fy1:
            continue
        if im is None:
            frame[fy0:fy1, fx0:fx1] = (frame[fy0:fy1, fx0:fx1] * (1 - alpha)).astype(np.uint8)
        else:
            frame[fy0:fy1, fx0:fx1] = im[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--speed', type=float, default=14)
    ap.add_argument('--seed', type=int, default=7)
    ap.add_argument('--repeat', type=int, default=1, help='같은 사진 묶음을 몇 번 반복할지 (영상 길이 늘리기)')
    ap.add_argument('--name', default='metal_conveyor')
    ap.add_argument('--test-from', type=Path, default=None,
                    help='Roboflow MSDD v9 압축을 푼 폴더: msdd_v1 test 사진 전체(results/msdd/meta.csv)를 모델로 고르지 않고 쓴다')
    a = ap.parse_args()
    rng = random.Random(a.seed)
    from ultralytics import YOLO
    model = YOLO(str(MODEL))

    items, dropped = [], []
    if a.test_from:
        src_names = yaml.safe_load((a.test_from / 'data.yaml').read_text(encoding='utf-8'))['names']
        meta = [r.split(',') for r in (ROOT / 'results/msdd/meta.csv').read_text(encoding='utf-8-sig').splitlines()[1:]]
        for name in sorted(r[0] for r in meta if r[1] == 'test'):
            p = next((q for q in (a.test_from / s / 'images' / name for s in ('train', 'valid', 'test')) if q.exists()), None)
            if p is None:
                dropped.append({'case': 'missing', 'image': Path(name)})
                continue
            labels = []          # v9 라벨 → 모델 클래스 이름 ('Normal' 전체 윤곽은 msdd_v1 처럼 버림)
            for line in (p.parent.parent / 'labels' / f'{p.stem}.txt').read_text().splitlines():
                v = line.split()
                if len(v) >= 7 and src_names[int(v[0])] in NAMES:
                    xs, ys = np.array(v[1::2], float), np.array(v[2::2], float)
                    labels.append((src_names[int(v[0])], (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2,
                                   xs.max() - xs.min(), ys.max() - ys.min()))
            items.append({'image': p, 'img': cv2.imread(str(p)), 'labels': labels,
                          'case': labels[0][0] if labels else 'normal', 'kind': 'defect' if labels else 'normal'})
    for case_dir in [] if a.test_from else sorted(p for p in SRC.iterdir() if p.is_dir()):
        case = case_dir.name.split('_', 1)[1]
        normal = case.lower() == 'normal'
        for p in sorted((case_dir / 'originals/images').glob('*.jpg')):
            img = cv2.imread(str(p))
            labels = read_labels(case_dir / 'originals/labels' / f'{p.stem}.txt')
            if normal:
                sq = cv2.imdecode(cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 40])[1], cv2.IMREAD_COLOR)
                ok = not labels and all(len(r.boxes) == 0 for r in model.predict([img, sq], imgsz=IMGSZ, conf=NORMAL_CONF, verbose=False))
            else:
                ok = bool(labels) and perfect(model.predict(img, imgsz=IMGSZ, conf=CONF, verbose=False)[0], labels)
            (items if ok else dropped).append({'image': p, 'img': img, 'labels': labels, 'case': 'normal' if normal else case,
                                               'kind': 'normal' if normal else 'defect'})
    print('items:', {c: sum(i['case'] == c for i in items) for c in sorted({i['case'] for i in items})},
          'dropped:', [(d['case'], d['image'].name[:20]) for d in dropped])
    seq = []
    for _ in range(a.repeat):
        batch = items[:]
        rng.shuffle(batch)
        seq += [dict(x) for x in batch]

    pitch, lead = BW + GAP, LEAD * a.speed
    n_frames = int(np.ceil((W + lead + (len(seq) - 1) * pitch + BW + 20) / a.speed))
    for i, b in enumerate(seq):
        b['y'] = (H - BH) // 2 + rng.randint(-6, 6)
        b['x0'] = W + lead + i * pitch
        b['enter_frame'] = int((b['x0'] - W) / a.speed)
        b['center_frame'] = int(round((b['x0'] - (W - BW) / 2) / a.speed))
        b['exit_frame'] = int(np.ceil((b['x0'] + BW) / a.speed))

    OUT.mkdir(parents=True, exist_ok=True)
    mp4 = OUT / f'{a.name}.mp4'
    writer = cv2.VideoWriter(str(mp4), cv2.VideoWriter_fourcc(*'avc1'), FPS, (W, H))
    if not writer.isOpened():
        sys.exit('video writer failed (avc1)')
    bg, vignette = belt_background()
    for f in range(n_frames):
        shift = f * a.speed
        frame = bg.copy()
        for x in range(-(int(shift) % 96), W, 96):
            if 0 <= x < W:
                frame[BELT_TOP + 1:BELT_BOTTOM - 1, x:x + 3] = SEAM
        for b in seq:
            x = int(round(b['x0'] - shift))
            if x < W and x + BW > 0:
                paste(frame, b['img'], x, b['y'])
        writer.write((frame * vignette).astype(np.uint8))
    writer.release()

    manifest = {
        'video': mp4.name, 'domain': 'msdd', 'fps': FPS, 'size': [W, H], 'board_px': BW, 'board_w': BW, 'board_h': BH,
        'belt_bgr': list(BELT), 'speed_px_per_frame': a.speed, 'frames': n_frames, 'seconds': round(n_frames / FPS, 1),
        'seed': a.seed, 'sensing_zone': [(W - BW) // 2, (H - BH) // 2, (W + BW) // 2, (H + BH) // 2],
        'note': 'x of an item at frame f = x0 - f*speed. Labels are normalized boxes (from the seg polygons).',
        'boards': [{'index': i, 'kind': b['kind'], 'case': b['case'],
                    'source': (b['image'].relative_to(ROOT) if b['image'].is_relative_to(ROOT) else b['image']).as_posix(),
                    'x0': b['x0'], 'y': b['y'], 'enter_frame': b['enter_frame'], 'center_frame': b['center_frame'],
                    'exit_frame': b['exit_frame'],
                    'labels': [{'type': t, 'cx': cx, 'cy': cy, 'w': w, 'h': h} for t, cx, cy, w, h in b['labels']]}
                   for i, b in enumerate(seq)],
    }
    (OUT / f'{a.name}.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'saved {mp4} ({len(seq)} items, {n_frames} frames, {n_frames / FPS:.1f}s, {mp4.stat().st_size / 1e6:.1f} MB)')


if __name__ == '__main__':
    main()
