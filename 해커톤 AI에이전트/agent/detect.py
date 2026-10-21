"""① 본다 + ③ 판단한다: YOLO 추론 → 결함 목록 → 정상 / 의심(재검사, Hold) / 이상 판정.

판정 규칙은 코드로 고정하고, 기준값과 유형별 예외는 knowledge/defect_taxonomy_<domain>.yaml 의 judgment 에 둔다.
큰 사진은 학습 크기(640) 조각으로 잘라 추론한 뒤 합친다 (타일링).
"""
import re
from pathlib import Path

import cv2
import numpy as np
import torch
import yaml
from torchvision.ops import nms
from ultralytics import YOLO
from ultralytics.utils.plotting import Annotator, colors

from agent.device import pick_device
from agent.i18n import reason_text

ROOT = Path(__file__).resolve().parents[1]
MODELS = {
    'pcb':  (ROOT / 'models/pcb_v2_yolo11s.pt', 640),
    'msdd': (ROOT / 'models/msdd_v1_yolo11s_seg.pt', 512),
    'mobile': (ROOT / 'models/mobile_surface_yolo11s_seg.pt', 512),
}
TAXONOMIES = {d: yaml.safe_load((ROOT / f'knowledge/defect_taxonomy_{d}.yaml').read_text(encoding='utf-8'))
              for d in MODELS}
TAXONOMY = TAXONOMIES['pcb']         # 하위 호환
# 모델이 학습 때 본 원본 사진 크기 (가로, 세로). 타일 조각을 이 크기로 잘라야 결함 크기가 학습 때와 같아진다.
# pcb 는 640 조각, msdd 는 512 사진, mobile 은 1920×1080 사진을 512 로 줄여 학습했다.
NATIVE = {'pcb': (640, 640), 'msdd': (512, 512), 'mobile': (1920, 1080)}
TILE_TRIGGER = 1.5                   # 사진이 학습 사진 크기의 이 배수를 넘으면 타일링
TILE_OVERLAP = 0.2
CROP_PAD = 24                        # 결함 확대 이미지 여백(px)
_cache = {}
_devices = {}


def thresholds(domain):
    return TAXONOMIES[domain]['judgment']


def _model(domain):
    if domain not in _cache:
        _cache[domain] = YOLO(str(MODELS[domain][0]))
    return _cache[domain]


def device_for(domain):
    """모델별 장치: 처음 쓸 때 한 번 정한다 (GPU 우선, 다른 프로세스가 GPU 를 바쁘게 쓰면 CPU). ultralytics 는 첫 추론 뒤 장치를 바꾸지 않는다."""
    if domain not in _devices:
        _devices[domain] = pick_device(need_mb=1500)
    return _devices[domain]


def _position(cx, cy, w, h):
    """이미지를 3×3 으로 나눠 위치를 한글로 표현."""
    row = ['상단', '중앙', '하단'][min(int(3 * cy / h), 2)]
    col = ['좌측', '중앙', '우측'][min(int(3 * cx / w), 2)]
    return '중앙' if row == col == '중앙' else f'{row} {col}'


def _poly_area(xyn):
    """정규화 폴리곤 → 이미지 대비 면적 비율."""
    if len(xyn) < 3:
        return 0.0
    x, y = xyn[:, 0], xyn[:, 1]
    return float(0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1))))


def _tile_origins(length, size, overlap):
    if length <= size:
        return [0]
    stride = int(size * (1 - overlap))
    xs = list(range(0, length - size + 1, stride))
    if xs[-1] + size < length:
        xs.append(length - size)
    return xs


def _window(domain, w, h):
    """학습 사진 크기 조각 (사진이 세로로 길면 가로·세로를 바꾼다)."""
    ww, wh = NATIVE[domain]
    return (wh, ww) if (h > w) != (wh > ww) and ww != wh else (ww, wh)


def needs_tiling(domain, w, h):
    ww, wh = _window(domain, w, h)
    return max(w / ww, h / wh) > TILE_TRIGGER


def _merge(boxes, scores, cls, iou=0.5, contain=0.7):
    """조각 경계에서 중복된 박스 제거: 클래스별 NMS + 작은 박스가 큰 박스에 대부분 포함되면 제거."""
    keep_all = []
    for c in cls.unique():
        idx = (cls == c).nonzero().flatten()
        idx = idx[nms(boxes[idx], scores[idx], iou)]
        b = boxes[idx]
        area = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
        lt = torch.max(b[:, None, :2], b[None, :, :2])
        rb = torch.min(b[:, None, 2:], b[None, :, 2:])
        inter = (rb - lt).clamp(min=0).prod(2)
        drop = set()
        for i in range(len(idx)):            # 점수 높은 순으로 정렬돼 있음
            for j in range(i + 1, len(idx)):
                if j not in drop and i not in drop and inter[i, j] / min(area[i], area[j]) > contain:
                    drop.add(j)
        keep_all += [int(idx[k]) for k in range(len(idx)) if k not in drop]
    return torch.tensor(sorted(keep_all), dtype=torch.long)


def _predict_tiled(model, img, imgsz, conf, domain='pcb'):
    """사진을 학습 사진 크기(NATIVE) 조각으로 잘라 추론 → 합치기. 세그멘테이션 모델은 마스크 면적도 돌려준다."""
    h, w = img.shape[:2]
    ww, wh = _window(domain, w, h)
    origins = [(x, y) for y in _tile_origins(h, wh, TILE_OVERLAP) for x in _tile_origins(w, ww, TILE_OVERLAP)]
    crops = [img[y:y + wh, x:x + ww] for x, y in origins]
    boxes, scores, cls, areas = [], [], [], []
    for (x, y), r in zip(origins, model.predict(crops, imgsz=imgsz, conf=conf, verbose=False, device=device_for(domain))):
        if not len(r.boxes):
            continue
        boxes.append(r.boxes.xyxy.cpu() + torch.tensor([x, y, x, y]))
        scores.append(r.boxes.conf.cpu())
        cls.append(r.boxes.cls.cpu())
        ch, cw = r.orig_shape
        areas += [_poly_area(p) * cw * ch / (w * h) for p in r.masks.xyn] if r.masks is not None else [None] * len(r.boxes)
    if not boxes:
        return [], len(origins)
    boxes, scores, cls = torch.cat(boxes), torch.cat(scores), torch.cat(cls)
    keep = _merge(boxes, scores, cls)
    return [(boxes[k].tolist(), float(scores[k]), int(cls[k]), areas[k]) for k in keep], len(origins)


def classify(d, domain):
    """결함 1개 → (의심 review / 이상 reject, 근거 키, 근거 값). 유형별 규칙은 taxonomy 의 judgment.rules.

    근거 문장은 언어별로 agent.i18n.reason_text 가 만든다. 확인 방법(rule 의 note)은 재검사 의뢰서(Hold)에 따로 적는다.
    """
    th = thresholds(domain)
    rule = th.get('rules', {}).get(d['type'], {})
    cut = rule.get('reject_conf', th['conf_reject'])
    args = {'conf': d['conf'], 'cut': cut}
    if d['conf'] < cut:
        return 'review', 'below_cut', args
    if rule.get('max_level') == 'review':
        return 'review', 'max_review', args
    if rule.get('require_surface') and d.get('extent') != '전면':
        return 'review', 'local_only', args
    if 'min_area' in rule and d.get('area_ratio', 1.0) < rule['min_area']:
        return 'review', 'small_area', {**args, 'area': 100 * d.get('area_ratio', 0), 'min': 100 * rule['min_area']}
    return 'reject', 'above_cut', {**args, 'lowered': cut < th['conf_reject'], 'surface': d.get('extent') == '전면'}


def judge(defects, domain='pcb'):
    levels = {d['level'] for d in defects}
    return 'reject' if 'reject' in levels else 'review' if levels else 'normal'


def detect(image_path, domain='pcb', save_dir=None, tile=None):
    """사진 1장 → {'verdict', 'defects', 'marked_image', 'crops', ...}.

    tile: None 이면 사진 크기로 자동 결정, True/False 로 강제.
    """
    _, imgsz = MODELS[domain]
    th = thresholds(domain)
    model = _model(domain)
    img = cv2.imread(str(image_path))
    if img is None:
        raise FileNotFoundError(image_path)
    h, w = img.shape[:2]
    if tile is None:
        tile = needs_tiling(domain, w, h)

    if tile:
        raw, n_tiles = _predict_tiled(model, img, imgsz, th['conf_review'], domain)
        r = None
    else:
        r = model.predict(img, imgsz=imgsz, conf=th['conf_review'], verbose=False, device=device_for(domain))[0]
        n_tiles = 1
        areas = [_poly_area(p) for p in r.masks.xyn] if r.masks is not None else [None] * len(r.boxes)
        raw = [(b.tolist(), float(c), int(k), a) for b, c, k, a in zip(r.boxes.xyxy, r.boxes.conf, r.boxes.cls, areas)]

    defects = []
    for (x0, y0, x1, y1), conf, c, area in sorted(raw, key=lambda t: -t[1]):
        d = {'id': len(defects) + 1,
             'type': model.names[c],
             'conf': round(conf, 3),
             'box_px': [round(x0), round(y0), round(x1), round(y1)],
             'size_px': [round(x1 - x0), round(y1 - y0)],
             'position': _position((x0 + x1) / 2, (y0 + y1) / 2, w, h)}
        if area is not None:         # 세그멘테이션: 실제 결함 면적 비율, 전면 분포 여부
            d['area_ratio'] = round(area, 5)
            d['extent'] = '전면' if area >= th.get('surface_ratio', 1.0) else '국부'
        d['level'], d['reason_key'], d['reason_args'] = classify(d, domain)
        d['reason'] = reason_text(d, 'ko')
        defects.append(d)

    out = {'image': str(image_path), 'domain': domain, 'image_size': [w, h], 'tiles': n_tiles,
           'verdict': judge(defects, domain), 'defects': defects, 'marked_image': None, 'crops': []}
    if save_dir:
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        stem = Path(image_path).stem
        if r is not None:
            marked_img = r.plot()
        else:
            ann = Annotator(img.copy(), line_width=max(2, round(max(h, w) / 600)))
            for d in defects:
                ann.box_label(d['box_px'], f'{d["type"]} {d["conf"]:.2f}', color=colors(list(model.names.values()).index(d['type']), True))
            marked_img = ann.result()
        marked = save_dir / f'{stem}_marked.jpg'
        cv2.imwrite(str(marked), marked_img)
        out['marked_image'] = str(marked)
        for d in defects:            # 판정 근거: 결함 확대 이미지
            x0, y0, x1, y1 = d['box_px']
            crop = img[max(y0 - CROP_PAD, 0):min(y1 + CROP_PAD, h), max(x0 - CROP_PAD, 0):min(x1 + CROP_PAD, w)]
            p = save_dir / f'{stem}_crop{d["id"]}.jpg'
            cv2.imwrite(str(p), crop)
            d['crop'] = str(p)
            out['crops'].append(str(p))
    return out


_PART_RE = re.compile(r'(\d{5}_[^_]+-)_CAM\d_(CAP\d(?:_(?:UPPER|LOWER|LEFT|RIGHT))?)_(?:OK|NG)')
VERDICT_ORDER = {'reject': 0, 'review': 1, 'normal': 2}


def parse_view(image_path):
    """MSDD 파일명 → (부품번호, 촬영 위치). 예: 01078_N31824-40-_CAM1_CAP4_LOWER_NG… → ('01078_N31824-40-', 'CAP4_LOWER')."""
    m = _PART_RE.search(Path(image_path).name)
    return (m.group(1), m.group(2)) if m else (None, Path(image_path).stem)


def detect_part(image_paths, domain='msdd', save_dir=None, part_id=None):
    """부품 1개의 여러 방향 사진 → 부품 단위 판정. 하나라도 이상이면 이상, 이상 없이 의심이 있으면 의심."""
    views, defects = [], []
    for p in image_paths:
        det = detect(p, domain, save_dir)
        pid, cap = parse_view(p)
        part_id = part_id or pid
        views.append({'image': det['image'], 'marked_image': det['marked_image'], 'view': cap,
                      'verdict': det['verdict'], 'n_defects': len(det['defects'])})
        defects += [{**d, 'view': cap} for d in det['defects']]
    defects.sort(key=lambda d: -d['conf'])
    for i, d in enumerate(defects, 1):
        d['id'] = i
    verdict = min((v['verdict'] for v in views), key=VERDICT_ORDER.get) if views else 'normal'
    return {'image': views[0]['image'], 'domain': domain, 'part': part_id, 'views': views,
            'verdict': verdict, 'defects': defects, 'marked_image': views[0]['marked_image'],
            'crops': [d['crop'] for d in defects if d.get('crop')]}
