"""빠른 재학습: 현장에서 모은 라벨 사진을 기존 데이터에 섞어 모델을 이어서 학습하고, 좋아졌을 때만 교체한다.

절차
  1. 현장 폴더(<폴더>/ 사진 + <폴더>/labels/*.txt, tools/autolabel.py 로 만들고 작업자가 고친 것)를
     90% 학습 / 10% 검증으로 나눠 기존 학습 데이터에 추가한다. 정상 사진(빈 라벨)도 그대로 넣는다.
  2. 지금 모델 weights 에서 낮은 학습률로 이어서 학습한다 (기본 30 epoch).
  3. 기존 test 셋과 현장 검증 셋 모두에서 F1 을 비교한다. 기존 test F1 이 떨어지지 않고 현장 F1 이 오르면 models/ 를 교체
     (이전 모델은 models/backup/ 에 보관).

사용: python tools/quick_train.py <현장 폴더> --domain mobile [--epochs 30] [--dry-run]
"""
import argparse
import random
import shutil
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ultralytics import YOLO  # noqa: E402

from agent.detect import MODELS  # noqa: E402

BASE_DATA = {
    'pcb': ROOT.parent / 'data/huggingface/pcb-defect-v2/data.yaml',
    'msdd': ROOT.parent / 'data/huggingface/metal-surface-defect-v1/data.yaml',
    'mobile': ROOT.parent / 'data/mobile_surface/data.yaml',
}
IMG_EXT = {'.jpg', '.jpeg', '.png', '.bmp'}


def f1(m):
    p, r = m.box.mp, m.box.mr
    return 2 * p * r / (p + r + 1e-9)


def split_dirs(cfg_path, key):
    cfg = yaml.safe_load(Path(cfg_path).read_text(encoding='utf-8'))
    root = Path(cfg.get('path', Path(cfg_path).parent))
    if not root.is_absolute():
        root = (Path(cfg_path).parent / root).resolve()
    p = Path(cfg[key])
    return p if p.is_absolute() else (root / p).resolve()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder')
    ap.add_argument('--domain', required=True, choices=list(MODELS))
    ap.add_argument('--epochs', type=int, default=30)
    ap.add_argument('--dry-run', action='store_true', help='데이터 구성만 만들고 학습하지 않는다')
    a = ap.parse_args()

    folder = Path(a.folder)
    imgs = sorted(p for p in folder.iterdir() if p.suffix.lower() in IMG_EXT and (folder / 'labels' / f'{p.stem}.txt').exists())
    if len(imgs) < 10:
        sys.exit(f'라벨이 있는 사진이 {len(imgs)}장뿐입니다 (최소 10장). tools/autolabel.py 로 라벨을 만들고 검토하세요.')
    random.Random(0).shuffle(imgs)
    n_val = max(2, len(imgs) // 10)
    field = {'val': imgs[:n_val], 'train': imgs[n_val:]}

    stamp = time.strftime('%Y%m%d_%H%M%S')
    work = ROOT / 'runs/quick' / f'{a.domain}_{stamp}'
    base_yaml = BASE_DATA[a.domain]
    base = yaml.safe_load(base_yaml.read_text(encoding='utf-8'))
    for split, items in field.items():
        for sub in ('images', 'labels'):
            (work / split / sub).mkdir(parents=True, exist_ok=True)
        for p in items:
            shutil.copy2(p, work / split / 'images' / p.name)
            shutil.copy2(folder / 'labels' / f'{p.stem}.txt', work / split / 'labels' / f'{p.stem}.txt')
    data = {'path': str(work), 'nc': base['nc'], 'names': base['names'],
            'train': [str(split_dirs(base_yaml, 'train')), 'train/images'],
            'val': [str(split_dirs(base_yaml, 'val')), 'val/images']}
    (work / 'data.yaml').write_text(yaml.safe_dump(data, allow_unicode=True), encoding='utf-8')
    field_yaml = {**data, 'train': 'train/images', 'val': 'val/images', 'test': 'val/images'}
    (work / 'field.yaml').write_text(yaml.safe_dump(field_yaml, allow_unicode=True), encoding='utf-8')
    print(f'구성: 현장 학습 {len(field["train"])}장 + 기존 학습 데이터 / 현장 검증 {len(field["val"])}장 → {work}')
    if a.dry_run:
        return

    weights, imgsz = MODELS[a.domain]
    old = YOLO(str(weights))
    base_test = {**base, 'path': str(base_yaml.parent)}
    base_eval = work / 'base_eval.yaml'
    base_eval.write_text(yaml.safe_dump({**base_test, 'val': str(split_dirs(base_yaml, 'test'))}, allow_unicode=True), encoding='utf-8')
    before_base = f1(old.val(data=str(base_eval), imgsz=imgsz, verbose=False, plots=False))
    before_field = f1(old.val(data=str(work / 'field.yaml'), imgsz=imgsz, verbose=False, plots=False))

    model = YOLO(str(weights))
    model.train(data=str(work / 'data.yaml'), epochs=a.epochs, imgsz=imgsz, batch=16, lr0=0.002, lrf=0.1, cos_lr=True,
                warmup_epochs=1, close_mosaic=5, patience=15, project=str(work), name='train', plots=False)
    new = YOLO(str(work / 'train/weights/best.pt'))
    after_base = f1(new.val(data=str(base_eval), imgsz=imgsz, verbose=False, plots=False))
    after_field = f1(new.val(data=str(work / 'field.yaml'), imgsz=imgsz, verbose=False, plots=False))
    print(f'기존 test F1 {before_base:.3f} → {after_base:.3f} / 현장 검증 F1 {before_field:.3f} → {after_field:.3f}')
    if after_base >= before_base - 0.01 and after_field > before_field:
        backup = ROOT / 'models/backup'
        backup.mkdir(exist_ok=True)
        shutil.copy2(weights, backup / f'{weights.stem}_{stamp}.pt')
        shutil.copy2(work / 'train/weights/best.pt', weights)
        print(f'모델 교체 완료: {weights.name} (이전 모델 → models/backup/)')
    else:
        print('개선이 확인되지 않아 모델을 교체하지 않았습니다 (결과는 위 폴더에 남아 있음).')


if __name__ == '__main__':
    main()
