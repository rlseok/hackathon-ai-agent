"""가상 컨베이어 영상 (혼합 라인): 벨트 하나에 PCB·금속·액정(휴대폰 표면) 제품이 무작위로 섞여 온다.

- 사진: 세 라인 영상(videos/<line>_conveyor.json)에 쓰인 같은 제품들에서 라인마다 --per 개씩 (정상 비율 유지).
  PCB 정상 기판은 make_conveyor_video.py 와 같은 방법(결함 자리를 같은 기판의 깨끗한 무늬로 메움)으로 다시 만든다.
- 크기: 라인 영상과 같다 — PCB 640×640, 금속 512×512, 액정 960×540. 그래서 제품마다 센싱 구역에서 자를 크기가 다르다.
  영상 서버의 분배 에이전트(agent/line_router.py)가 제품 종류를 가린 뒤 그 크기로 잘라 그 종류의 모델로 검사한다.
- 벨트: 짙은 파랑 한 색. 회색은 금속면·휴대폰 배경과 겹치고, 초록·검정은 PCB·금속 배경과 겹친다.
  짙은 파랑은 액정 라인에서 이미 검증됐고, 금속(검정 배경)·PCB(초록)와도 채널 차이가 45 이상이다.

출력: videos/mixed_conveyor.mp4, videos/mixed_conveyor.json (기존 형식 + domain='mixed', sizes, 제품마다 domain·board_w/h)
실행: .venv\\Scripts\\python tools/make_mixed_video.py [--per 30] [--speed 16] [--seed 7]
"""
import argparse
import json
import random
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from make_conveyor_video import load_boards, remove_defects  # noqa: E402

OUT = ROOT / 'videos'
LINES = {'pcb': 'pcb', 'metal': 'msdd', 'phone': 'mobile'}      # 라인 영상 → domain
SIZES = {'pcb': (640, 640), 'msdd': (512, 512), 'mobile': (960, 540)}

W, H, FPS = 1280, 720, 30
GAP = 200                    # 제품 사이 간격 (분배 에이전트가 이웃 제품을 하나로 보지 않게 라인 영상보다 넓게)
LEAD = 30
BELT_TOP, BELT_BOTTOM = 26, H - 26
BELT = (92, 52, 18)          # 짙은 파랑 (BGR)
SEAM = (104, 62, 26)


def load_items(per, rng, suffix=''):
    """세 라인 영상 json 의 제품 → 라인마다 per 개 (정상 비율 유지). 사진은 원본에서 다시 읽는다 (영상 재압축 없이)."""
    pcb_src = {b['image'].as_posix(): b for b in load_boards()}
    items = []
    for line, dom in LINES.items():
        boards = json.loads((OUT / f'{line}_conveyor{suffix}.json').read_text(encoding='utf-8'))['boards']
        normals = [b for b in boards if b['kind'] == 'normal']
        defects = [b for b in boards if b['kind'] == 'defect']
        n_norm = round(per * len(normals) / len(boards))
        pick = rng.sample(defects, per - n_norm) + rng.sample(normals, n_norm)
        bw, bh = SIZES[dom]
        for b in pick:
            img = cv2.imread(str(ROOT / b['source']))
            if dom == 'pcb' and b['kind'] == 'normal':       # 원래 라벨로 결함을 지운 기판
                erased = [(l[0], *l[1:]) for l in b['erased_labels']] if 'erased_labels' in b else pcb_src[(ROOT / b['source']).as_posix()]['labels']
                img, _ = remove_defects(img, erased)
            if img.shape[:2] != (bh, bw):
                img = cv2.resize(img, (bw, bh), interpolation=cv2.INTER_AREA)
            items.append({'domain': dom, 'line': line, 'kind': b['kind'], 'case': b['case'], 'source': b['source'],
                          'line_index': b['index'], 'img': img, 'w': bw, 'h': bh, 'labels': b['labels']})
    return items


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
    for dx, dy, im, alpha in ((10, 10, None, 0.4), (0, 0, img, 1.0)):
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
    ap.add_argument('--per', type=int, default=30, help='라인마다 제품 수')
    ap.add_argument('--speed', type=float, default=16)
    ap.add_argument('--seed', type=int, default=7)
    ap.add_argument('--name', default='mixed_conveyor')
    ap.add_argument('--suffix', default='', help='세 라인 영상 세트: videos/<line>_conveyor<suffix>.json 에서 제품을 고른다')
    a = ap.parse_args()
    rng = random.Random(a.seed)
    seq = load_items(a.per, rng, a.suffix)
    rng.shuffle(seq)
    print('items:', {d: sum(i['domain'] == d for i in seq) for d in SIZES},
          'normal:', sum(i['kind'] == 'normal' for i in seq))

    x = W + LEAD * a.speed
    for b in seq:
        b['y'] = (H - b['h']) // 2 + rng.randint(-6, 6)
        b['x0'] = x
        b['enter_frame'] = int((x - W) / a.speed)
        b['center_frame'] = int(round((x - (W - b['w']) / 2) / a.speed))
        b['exit_frame'] = int(np.ceil((x + b['w']) / a.speed))
        x += b['w'] + GAP
    n_frames = int(np.ceil((x - GAP + 20) / a.speed))

    OUT.mkdir(parents=True, exist_ok=True)
    mp4 = OUT / f'{a.name}.mp4'
    writer = cv2.VideoWriter(str(mp4), cv2.VideoWriter_fourcc(*'avc1'), FPS, (W, H))
    if not writer.isOpened():
        sys.exit('video writer failed (avc1)')
    bg, vignette = belt_background()
    for f in range(n_frames):
        shift = f * a.speed
        frame = bg.copy()
        for sx in range(-(int(shift) % 96), W, 96):
            if 0 <= sx < W:
                frame[BELT_TOP + 1:BELT_BOTTOM - 1, sx:sx + 3] = SEAM
        for b in seq:
            bx = int(round(b['x0'] - shift))
            if bx < W and bx + b['w'] > 0:
                paste(frame, b['img'], bx, b['y'])
        writer.write((frame * vignette).astype(np.uint8))
    writer.release()

    manifest = {
        'video': mp4.name, 'domain': 'mixed', 'fps': FPS, 'size': [W, H], 'board_px': 640, 'board_w': 640, 'board_h': 640,
        'sizes': {d: list(s) for d, s in SIZES.items()}, 'belt_bgr': list(BELT), 'speed_px_per_frame': a.speed,
        'frames': n_frames, 'seconds': round(n_frames / FPS, 1), 'seed': a.seed,
        'note': 'x of an item at frame f = x0 - f*speed. Each item has its own domain and size (board_w/h); '
                'labels are normalized boxes on that item.',
        'boards': [{'index': i, 'domain': b['domain'], 'line': b['line'], 'line_index': b['line_index'], 'kind': b['kind'],
                    'case': b['case'], 'source': b['source'], 'board_w': b['w'], 'board_h': b['h'], 'x0': b['x0'],
                    'y': b['y'], 'enter_frame': b['enter_frame'], 'center_frame': b['center_frame'],
                    'exit_frame': b['exit_frame'], 'labels': b['labels']} for i, b in enumerate(seq)],
    }
    (OUT / f'{a.name}.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'saved {mp4} ({len(seq)} items, {n_frames} frames, {n_frames / FPS:.1f}s, {mp4.stat().st_size / 1e6:.1f} MB)')


if __name__ == '__main__':
    main()
