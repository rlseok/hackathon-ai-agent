"""가상 컨베이어 영상 (액정 라인): 휴대폰 표면 사진을 컨베이어 위로 흘려보내는 '카메라' 영상을 만든다.

- 사진: data/mobile_surface 의 test 사진 중 모델이 정답을 모두 맞힌 사진(유형별 최대 --per 장) + 결함 없는 사진(정상).
  정상 사진은 데이터셋에 원래 있는 것(빈 라벨)만 쓴다 — PCB 처럼 결함을 지워 만들지 않는다.
- 크기: 원본 1920×1080 → 960×540 으로 줄여 벨트에 올린다. 화면 가운데 960×540 센싱 구역에서 잘라 모델에 넣으면
  모델이 학습한 축척(가로 512 로 축소)과 같아진다.
- 벨트: 휴대폰 사진 배경(회색)과 확실히 구분되는 짙은 파랑. 영상 서버는 '벨트 색과 다른 영역'으로 제품을 찾는다.

출력: videos/phone_conveyor.mp4, videos/phone_conveyor.json (PCB 영상 json 과 같은 형식 + domain, board_w/h, belt_bgr)
실행: .venv\\Scripts\\python tools/make_phone_video.py [--per 20] [--speed 20] [--seed 7]
"""
import argparse
import json
import random
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/mobile_surface'
OUT = ROOT / 'videos'
MODEL = ROOT / 'models/mobile_surface_yolo11s_seg.pt'
NAMES = ['oil', 'scratch', 'stain']
CASE = {'Oil': 'oil', 'Scr': 'scratch', 'Sta': 'stain'}

W, H, FPS = 1280, 720, 30
BW, BH = 960, 540            # 벨트 위 제품 크기 (원본의 1/2)
IMGSZ = 512                  # 모델 학습 크기
GAP = 200
LEAD = 30
BELT_TOP, BELT_BOTTOM = 26, H - 26
BELT = (92, 52, 18)          # 벨트 색 (BGR, 짙은 파랑)
SEAM = (104, 62, 26)         # 벨트 이음매 (벨트와 비슷하게 — 영상 서버가 제품으로 착각하지 않게)
CONF, NORMAL_CONF = 0.25, 0.10


def read_labels(path):
    """YOLO 세그멘테이션 라벨(class x1 y1 x2 y2 …) → [(종류, cx, cy, w, h)] 정규화 박스."""
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
    """정답 결함을 모두 같은 종류·IoU≥0.5 로 맞히고 오탐이 없으면 True (tools/showcase.py 와 같은 기준)."""
    gt = [(t, [(cx - w / 2) * BW, (cy - h / 2) * BH, (cx + w / 2) * BW, (cy + h / 2) * BH]) for t, cx, cy, w, h in labels]
    used = set()
    for b, c in sorted(zip(r.boxes.xyxy.tolist(), r.boxes.cls.tolist()), key=lambda x: 0):
        hit = [(iou(b, g), j) for j, (t, g) in enumerate(gt) if j not in used and t == NAMES[int(c)]]
        best = max(hit, default=(0, None))
        if best[0] < 0.5:
            return False
        used.add(best[1])
    return len(used) == len(gt)


def belt_background():
    bg = np.full((H, W, 3), BELT, np.uint8)
    for y0, y1 in ((0, BELT_TOP), (BELT_BOTTOM, H)):        # 금속 레일
        grad = np.linspace(150, 95, y1 - y0).astype(np.uint8)
        bg[y0:y1] = np.repeat(grad[:, None, None], W, 1).repeat(3, 2)
    for y in (BELT_TOP, BELT_BOTTOM - 1):
        bg[y] = (20, 20, 22)
    yy, xx = np.mgrid[0:H, 0:W]
    d = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2
    return bg, (1.0 - 0.08 * np.clip(d, 0, 1.5))[..., None]


def paste(frame, img, x, y):
    h, w = img.shape[:2]
    for dx, dy, im, alpha in ((10, 10, None, 0.45), (0, 0, img, 1.0)):
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
    ap.add_argument('--per', type=int, default=20, help='결함 유형별 최대 장 수')
    ap.add_argument('--speed', type=float, default=20)
    ap.add_argument('--seed', type=int, default=7)
    ap.add_argument('--name', default='phone_conveyor')
    ap.add_argument('--all-test', action='store_true',
                    help='고르지 않고 test 세트 전체(결함 + 정상)를 무작위 순서로 — 편향 없는 라인 정확도용')
    a = ap.parse_args()
    rng = random.Random(a.seed)
    from ultralytics import YOLO
    model = YOLO(str(MODEL))

    def load(p, split):
        img = cv2.resize(cv2.imread(str(p)), (BW, BH), interpolation=cv2.INTER_AREA)
        return {'image': p, 'split': split, 'img': img, 'labels': read_labels(DATA / 'labels' / split / f'{p.stem}.txt')}

    if a.all_test:           # 모델 결과로 고르지 않는다: test 사진 전부 (정상은 test 의 빈 라벨 사진만)
        seq = []
        for p in sorted(q for q in (DATA / 'images/test').iterdir() if q.suffix.lower() in ('.jpg', '.png')):
            it = load(p, 'test')
            tag = next((v for k, v in CASE.items() if f'_{k}_' in p.name), None)
            seq.append({**it, 'case': tag if it['labels'] else 'normal', 'kind': 'defect' if it['labels'] else 'normal'})
        rng.shuffle(seq)
        print('all test:', {c: sum(x['case'] == c for x in seq) for c in sorted({x['case'] for x in seq})})
    picked = {c: [] for c in NAMES}
    tests = [] if a.all_test else sorted((DATA / 'images/test').glob('*.jpg'))
    rng.shuffle(tests)
    for p in tests:
        tag = next((v for k, v in CASE.items() if f'_{k}_' in p.name), None)
        if tag is None or len(picked[tag]) >= a.per:
            continue
        it = load(p, 'test')
        if it['labels'] and perfect(model.predict(it['img'], imgsz=IMGSZ, conf=CONF, verbose=False)[0], it['labels']):
            picked[tag].append({**it, 'case': tag, 'kind': 'defect'})
    # 정상 사진: 데이터셋 전체의 빈 라벨 사진 중 낮은 기준·압축 후에도 검출이 없는 것
    normals = []
    for split in () if a.all_test else ('test', 'val', 'train'):
        for lab in sorted((DATA / 'labels' / split).glob('*.txt')):
            if lab.read_text().strip():
                continue
            p = next((q for q in (DATA / 'images' / split / f'{lab.stem}{e}' for e in ('.jpg', '.png')) if q.exists()), None)
            if p is None:            # 정상 사진은 .png 로 들어 있다
                continue
            it = load(p, split)
            sq = cv2.imdecode(cv2.imencode('.jpg', it['img'], [cv2.IMWRITE_JPEG_QUALITY, 40])[1], cv2.IMREAD_COLOR)
            if all(len(r.boxes) == 0 for r in model.predict([it['img'], sq], imgsz=IMGSZ, conf=NORMAL_CONF, verbose=False)):
                normals.append({**it, 'case': 'normal', 'kind': 'normal'})
    if not a.all_test:
        seq = [x for v in picked.values() for x in v] + normals
        rng.shuffle(seq)
        print('picked:', {k: len(v) for k, v in picked.items()}, 'normal:', len(normals))

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
        'video': mp4.name, 'domain': 'mobile', 'fps': FPS, 'size': [W, H], 'board_px': BW, 'board_w': BW, 'board_h': BH,
        'belt_bgr': list(BELT), 'speed_px_per_frame': a.speed, 'frames': n_frames, 'seconds': round(n_frames / FPS, 1),
        'seed': a.seed, 'sensing_zone': [(W - BW) // 2, (H - BH) // 2, (W + BW) // 2, (H + BH) // 2],
        'note': 'x of an item at frame f = x0 - f*speed. Labels are normalized boxes on the 960x540 item (from the seg polygons).',
        'boards': [{'index': i, 'kind': b['kind'], 'case': b['case'], 'source': b['image'].relative_to(ROOT).as_posix(),
                    'split': b['split'], 'x0': b['x0'], 'y': b['y'], 'enter_frame': b['enter_frame'],
                    'center_frame': b['center_frame'], 'exit_frame': b['exit_frame'],
                    'labels': [{'type': t, 'cx': cx, 'cy': cy, 'w': w, 'h': h} for t, cx, cy, w, h in b['labels']]}
                   for i, b in enumerate(seq)],
    }
    (OUT / f'{a.name}.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'saved {mp4} ({len(seq)} items, {n_frames} frames, {n_frames / FPS:.1f}s, {mp4.stat().st_size / 1e6:.1f} MB)')


if __name__ == '__main__':
    main()
