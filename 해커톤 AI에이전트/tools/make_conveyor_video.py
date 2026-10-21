"""가상 컨베이어 영상: PCB 결함 사진(showcase 80장)을 컨베이어 위로 흘려보내는 '카메라' 영상을 만든다.

실시간 검사 시연의 입력용. 기판은 원본 크기(640×640, 학습 크기와 같음) 그대로 지나가므로
화면 가운데 센싱 구역에서 잘라 바로 검사할 수 있다.
일부 기판은 결함 자리를 주변 무늬로 메워 '정상 기판'으로 만들고, 모델이 아무것도 못 찾는 것만 쓴다.

출력: videos/pcb_conveyor.mp4 (H.264, 브라우저 재생 가능)
      videos/pcb_conveyor.json (기판 순서, 화면 위치·프레임, 정답 라벨, 모델 확인 결과)
실행: .venv\\Scripts\\python tools/make_conveyor_video.py [--speed 14] [--normal 0.25] [--seed 7]
"""
import argparse
import json
import random
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'results/pcb/showcase'
OUT = ROOT / 'videos'
MODEL = ROOT / 'models/pcb_v2_yolo11s.pt'
NAMES = ['falsecopper', 'missinghole', 'mousebite', 'opencircuit', 'pinhole', 'scratch', 'shortcircuit', 'spur']

W, H, FPS = 1280, 720, 30
BOARD = 640                  # 기판 크기 (모델 입력 크기와 같게)
GAP = 160                    # 기판 사이 간격 (px)
LEAD = 40                    # 시작 전 빈 벨트 길이 (프레임)
BELT_TOP, BELT_BOTTOM = 26, H - 26
CONF = 0.25                  # 모델 확인 기준 (판정 기준값 conf_review 와 같음)
NORMAL_CONF = 0.10           # 정상 기판은 이 낮은 기준에서도 검출이 없어야 채택 (영상 압축 후에도 정상으로 나오도록 여유)
MAX_DEFECT_PX = 70           # 정상 기판은 결함이 이보다 작은 기판에서만 만든다 (긴 스크래치처럼 큰 자리는 붙인 티가 남)


def load_boards():
    """showcase 원본 사진 + YOLO 라벨 → [{image, case, labels:[(cls, cx, cy, w, h)]}]."""
    boards = []
    for case_dir in sorted(p for p in SRC.iterdir() if p.is_dir()):
        img_dir, lab_dir = case_dir / 'originals/images', case_dir / 'originals/labels'
        for img in sorted(img_dir.glob('*.jpg')):
            lab = lab_dir / f'{img.stem}.txt'
            labels = []
            if lab.exists():
                for line in lab.read_text().splitlines():
                    v = line.split()
                    if len(v) == 5:
                        labels.append((NAMES[int(v[0])], *map(float, v[1:])))
            boards.append({'image': img, 'case': case_dir.name.split('_', 1)[1], 'labels': labels})
    return boards


def remove_defects(img, labels, pad=6, ring=14):
    """라벨 박스(조금 넓혀서)를 같은 기판의 비슷한 깨끗한 부분으로 바꿔 결함 없는 기판을 만든다.

    흐리게 번지는 inpaint 대신, 박스 둘레(ring)의 무늬와 가장 비슷한 곳을 같은 사진에서 찾아(마스크 템플릿 매칭)
    그 안쪽을 그대로 복사한다. PCB 는 패드·배선이 반복돼서 선명하게 메워진다. 이음매만 아주 살짝 섞는다.
    """
    out = img.copy()
    h, w = img.shape[:2]
    worst = 0.0                      # 복사해 온 조각 둘레가 원래 둘레와 얼마나 다른지 (RMS, 밝기 0~255) — 크면 티가 난다
    boxes = []
    for _, cx, cy, bw, bh in labels:
        boxes.append((max(int((cx - bw / 2) * w) - pad, 0), max(int((cy - bh / 2) * h) - pad, 0),
                      min(int((cx + bw / 2) * w) + pad, w), min(int((cy + bh / 2) * h) + pad, h)))
    bad = np.zeros((h, w), np.uint8)                      # 복사해 오면 안 되는 곳 (결함 자리)
    for x0, y0, x1, y1 in boxes:
        bad[max(y0 - ring, 0):y1 + ring, max(x0 - ring, 0):x1 + ring] = 1
    for x0, y0, x1, y1 in boxes:
        tx0, ty0, tx1, ty1 = max(x0 - ring, 0), max(y0 - ring, 0), min(x1 + ring, w), min(y1 + ring, h)
        tpl = out[ty0:ty1, tx0:tx1]
        tmask = np.full(tpl.shape[:2], 255, np.uint8)
        tmask[y0 - ty0:y1 - ty0, x0 - tx0:x1 - tx0] = 0     # 둘레만 비교
        score = cv2.matchTemplate(img, tpl, cv2.TM_SQDIFF, mask=cv2.merge([tmask] * 3))
        th, tw = tpl.shape[:2]
        # 결함 자리와 겹치는 후보는 제외
        integ = cv2.integral(bad)
        overlap = (integ[th:th + score.shape[0], tw:tw + score.shape[1]] - integ[:score.shape[0], tw:tw + score.shape[1]]
                   - integ[th:th + score.shape[0], :score.shape[1]] + integ[:score.shape[0], :score.shape[1]])
        score = np.where(overlap > 0, np.inf, np.nan_to_num(score, nan=np.inf, posinf=np.inf))
        if not np.isfinite(score).any():
            return out, 255.0                             # 붙일 곳이 없음 → 이 기판은 쓰지 않는다
        my, mx = np.unravel_index(int(np.argmin(score)), score.shape)
        worst = max(worst, float(np.sqrt(score[my, mx] / max(1, 3 * int((tmask > 0).sum())))))
        src = img[my + (y0 - ty0):my + (y1 - ty0), mx + (x0 - tx0):mx + (x1 - tx0)]
        # 이음매를 3px 정도만 부드럽게 섞는다
        alpha = np.ones(src.shape[:2], np.float32)
        alpha = cv2.GaussianBlur(cv2.copyMakeBorder(alpha[3:-3, 3:-3], 3, 3, 3, 3, cv2.BORDER_CONSTANT, value=0)
                                 if min(alpha.shape) > 8 else alpha, (5, 5), 0)[..., None]
        out[y0:y1, x0:x1] = (src * alpha + out[y0:y1, x0:x1] * (1 - alpha)).astype(np.uint8)
    return out, worst


def check(model, imgs, conf=CONF):
    """모델로 확인: 기판마다 (검출 수, 최고 신뢰도, 유형 목록)."""
    out = []
    for r in model.predict(imgs, imgsz=BOARD, conf=conf, verbose=False):
        cls = [NAMES[int(c)] for c in r.boxes.cls]
        conf = [float(c) for c in r.boxes.conf]
        out.append({'n_det': len(cls), 'max_conf': round(max(conf), 3) if conf else 0.0,
                    'types': sorted(set(cls))})
    return out


def belt_background():
    """정지한 부분: 위아래 레일 + 벨트 바탕색. 움직이는 무늬는 프레임마다 따로 그린다."""
    bg = np.full((H, W, 3), (38, 40, 44), np.uint8)
    for y0, y1 in ((0, BELT_TOP), (BELT_BOTTOM, H)):        # 금속 레일
        grad = np.linspace(150, 95, y1 - y0).astype(np.uint8)
        bg[y0:y1] = np.repeat(grad[:, None, None], W, 1).repeat(3, 2)
    for y in (BELT_TOP, BELT_BOTTOM - 1):
        bg[y] = (20, 20, 22)
    yy, xx = np.mgrid[0:H, 0:W]                               # 가장자리가 살짝 어두운 조명
    d = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2
    vignette = (1.0 - 0.10 * np.clip(d, 0, 1.5))[..., None]
    return bg, vignette


def draw_belt(frame, shift):
    """벨트 이음매(세로 줄)를 벨트와 같은 속도로 움직여 그린다."""
    pitch = 96
    for x in range(-(int(shift) % pitch), W, pitch):
        if 0 <= x < W:
            frame[BELT_TOP + 1:BELT_BOTTOM - 1, x:x + 3] = (52, 55, 60)


def paste(frame, img, x, y):
    """기판을 그림자와 함께 붙인다 (화면 밖으로 나간 부분은 잘라냄)."""
    for dx, dy, im, alpha in ((10, 10, None, 0.45), (0, 0, img, 1.0)):
        x0, y0 = x + dx, y + dy
        fx0, fx1 = max(x0, 0), min(x0 + BOARD, W)
        fy0, fy1 = max(y0, 0), min(y0 + BOARD, H)
        if fx0 >= fx1 or fy0 >= fy1:
            continue
        if im is None:                                        # 그림자
            frame[fy0:fy1, fx0:fx1] = (frame[fy0:fy1, fx0:fx1] * (1 - alpha)).astype(np.uint8)
        else:
            frame[fy0:fy1, fx0:fx1] = im[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--speed', type=float, default=14, help='벨트 속도 (px/프레임, 30fps)')
    ap.add_argument('--normal', type=float, default=0.25, help='정상 기판 비율 (결함 기판 수 대비)')
    ap.add_argument('--seed', type=int, default=7)
    ap.add_argument('--name', default='pcb_conveyor')
    a = ap.parse_args()
    rng = random.Random(a.seed)

    from ultralytics import YOLO
    model = YOLO(str(MODEL))

    boards = load_boards()
    for b in boards:
        b['img'] = cv2.imread(str(b['image']))
        b['kind'] = 'defect'
    # 정상 기판: 결함을 지운 뒤 모델이 아무것도 못 찾는 것만 채택
    want = round(len(boards) * a.normal)
    normals, pool = [], boards[:]
    rng.shuffle(pool)
    for b in pool:
        if len(normals) >= want:
            break
        if max((max(bw, bh) * BOARD for _, _, _, bw, bh in b['labels']), default=0) > MAX_DEFECT_PX:
            continue
        clean, _ = remove_defects(b['img'], b['labels'])
        # 영상 압축 뒤에도 정상으로 나와야 한다 → 원본과 강하게 압축한 사진 둘 다 확인
        squashed = cv2.imdecode(cv2.imencode('.jpg', clean, [cv2.IMWRITE_JPEG_QUALITY, 40])[1], cv2.IMREAD_COLOR)
        if all(c['n_det'] == 0 for c in check(model, [clean, squashed], NORMAL_CONF)):
            normals.append({'image': b['image'], 'case': 'normal', 'labels': [], 'img': clean, 'kind': 'normal'})
    seq = boards + normals
    rng.shuffle(seq)
    for b, c in zip(seq, check(model, [b['img'] for b in seq])):
        b['model'] = c
    print(f'boards: {len(boards)} defect + {len(normals)} normal (tried for {want})')

    pitch = BOARD + GAP
    lead = LEAD * a.speed
    n_frames = int(np.ceil((W + lead + (len(seq) - 1) * pitch + BOARD + 20) / a.speed))
    for i, b in enumerate(seq):
        b['y'] = (H - BOARD) // 2 + rng.randint(-6, 6)
        start = W + lead + i * pitch                        # shift=0 일 때 기판 왼쪽 x
        b['x0'] = start
        b['enter_frame'] = int((start - W) / a.speed)
        b['center_frame'] = int(round((start - (W - BOARD) / 2) / a.speed))   # 기판이 화면 가운데
        b['exit_frame'] = int(np.ceil((start + BOARD) / a.speed))

    OUT.mkdir(parents=True, exist_ok=True)
    mp4 = OUT / f'{a.name}.mp4'
    writer = cv2.VideoWriter(str(mp4), cv2.VideoWriter_fourcc(*'avc1'), FPS, (W, H))
    if not writer.isOpened():
        sys.exit('video writer failed (avc1)')
    bg, vignette = belt_background()
    for f in range(n_frames):
        shift = f * a.speed
        frame = bg.copy()
        draw_belt(frame, shift)
        for b in seq:
            x = int(round(b['x0'] - shift))
            if x < W and x + BOARD > 0:
                paste(frame, b['img'], x, b['y'])
        writer.write((frame * vignette).astype(np.uint8))
    writer.release()

    manifest = {
        'video': mp4.name, 'fps': FPS, 'size': [W, H], 'board_px': BOARD, 'speed_px_per_frame': a.speed,
        'frames': n_frames, 'seconds': round(n_frames / FPS, 1), 'seed': a.seed,
        'sensing_zone': [(W - BOARD) // 2, 0, (W + BOARD) // 2, H],
        'note': 'x of a board at frame f = x0 - f*speed. center_frame = board centered (inside the sensing zone).',
        'boards': [{'index': i, 'kind': b['kind'], 'case': b['case'],
                    'source': b['image'].relative_to(ROOT).as_posix(), 'x0': b['x0'], 'y': b['y'],
                    'enter_frame': b['enter_frame'], 'center_frame': b['center_frame'], 'exit_frame': b['exit_frame'],
                    'labels': [{'type': t, 'cx': cx, 'cy': cy, 'w': w, 'h': h} for t, cx, cy, w, h in b['labels']],
                    'model_check': b['model']} for i, b in enumerate(seq)],
    }
    (OUT / f'{a.name}.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding='utf-8')
    found = sum(b['model']['n_det'] > 0 for b in seq if b['kind'] == 'defect')
    print(f'saved {mp4} ({n_frames} frames, {n_frames / FPS:.1f}s, {mp4.stat().st_size / 1e6:.1f} MB)')
    print(f'model check: defect boards detected {found}/{len(boards)}, normal boards clean {len(normals)}/{len(normals)}')


if __name__ == '__main__':
    main()
