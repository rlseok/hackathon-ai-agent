"""노트북 이전용 패키지 폴더를 만든다. 원본은 건드리지 않고 모두 '복사'한다.

사용: python build_package.py <출력 폴더>
"""
import csv
import shutil
import sys
from pathlib import Path

DESKTOP = Path.home() / 'Desktop'
PROJECT = DESKTOP / 'defect_agent_project'
PCB = PROJECT / 'pcb_agent'
MSDD = PROJECT / 'msdd_agent'
HACKATHON_PDF = Path.home() / 'OneDrive' / '문서' / '카카오톡 받은 파일' / '국립창원대 AI Agent 해커톤 주제 안내.pdf'
PCB_V8 = Path.home() / 'Downloads' / 'PCB_Project.v8i.yolov11'

RUN_FILES = ['args.yaml', 'results.csv', 'results.png', 'confusion_matrix.png',
             'confusion_matrix_normalized.png', 'BoxPR_curve.png', 'BoxF1_curve.png',
             'BoxP_curve.png', 'BoxR_curve.png', 'MaskPR_curve.png', 'MaskF1_curve.png',
             'MaskP_curve.png', 'MaskR_curve.png', 'labels.jpg',
             'val_batch0_labels.jpg', 'val_batch0_pred.jpg']


def copy(src, dst):
    src, dst = Path(src), Path(dst)
    if not src.exists():
        print(f'  [skip, 없음] {src}')
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        shutil.copy2(src, dst)


def copy_run(run_dir, dst):
    for name in RUN_FILES:
        if (run_dir / name).exists():
            copy(run_dir / name, dst / name)


def copy_showcase(showcase_dir, data_root, split, dst):
    """비교 이미지 + 우수 사례의 원본 이미지/라벨을 케이스별로 복사."""
    copy(showcase_dir, dst)
    img_dir, lbl_dir = data_root / 'images' / split, data_root / 'labels' / split
    n = 0
    with open(showcase_dir / 'summary.csv', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            if not row['image']:
                continue
            case_dir = dst / row['case'] / 'originals'
            stem = Path(row['image']).stem
            copy(img_dir / row['image'], case_dir / 'images' / f'{int(row["rank"]):02d}_{row["image"]}')
            copy(lbl_dir / f'{stem}.txt', case_dir / 'labels' / f'{int(row["rank"]):02d}_{stem}.txt')
            n += 1
    print(f'  originals copied: {n}')


def main():
    out = Path(sys.argv[1])
    if out.exists():
        raise SystemExit(f'{out} 가 이미 있습니다. 다른 경로를 지정하세요.')

    print('models')
    copy(PCB / 'runs/detect/runs/pcb_v2_yolo11s/weights/best.pt', out / 'models/pcb_v2_yolo11s.pt')
    copy(MSDD / 'runs/train/msdd_v1_yolo11s_seg/weights/best.pt', out / 'models/msdd_v1_yolo11s_seg.pt')
    copy(PCB / 'data/pcb_v2/data.yaml', out / 'models/pcb_v2_data.yaml')
    copy(MSDD / 'data/msdd_v1/data.yaml', out / 'models/msdd_v1_data.yaml')

    print('knowledge')
    copy(PCB / 'taxonomy/defect_taxonomy.yaml', out / 'knowledge/defect_taxonomy_pcb.yaml')

    print('results: pcb')
    copy_showcase(PCB / 'showcase/pcb_v2', PCB / 'data/pcb_v2', 'test', out / 'results/pcb/showcase')
    copy_run(PCB / 'runs/detect/runs/pcb_v2_yolo11s', out / 'results/pcb/train_v2')
    copy_run(PCB / 'runs/eval/test', out / 'results/pcb/test_eval_v2')
    copy_run(PCB / 'runs/train/pcb_v3_ft', out / 'results/pcb/train_v3_ft (미채택)')
    copy_run(PCB / 'runs/eval/test_v3', out / 'results/pcb/test_eval_v3 (미채택)')
    copy(PCB / 'data/pcb_v2/split_groups.csv', out / 'results/pcb/split_groups.csv')

    print('results: msdd')
    copy_showcase(MSDD / 'showcase', MSDD / 'data/msdd_v1', 'test', out / 'results/msdd/showcase')
    copy_run(MSDD / 'runs/train/msdd_v1_yolo11s_seg', out / 'results/msdd/train_v1')
    copy_run(MSDD / 'runs/eval/test', out / 'results/msdd/test_eval_v1')
    copy(MSDD / 'data/msdd_v1/meta.csv', out / 'results/msdd/meta.csv')

    print('tools')
    for f in ['resplit.py', 'merge_extra.py', 'label_preview.py', 'showcase.py', 'build_package.py']:
        copy(PCB / 'tools' / f, out / 'tools' / f)
    copy(MSDD / 'tools/prepare_msdd.py', out / 'tools/prepare_msdd.py')
    copy(PCB / 'train.ps1', out / 'tools/ps1/pcb_train.ps1')
    copy(PCB / 'train_v3.ps1', out / 'tools/ps1/pcb_train_v3.ps1')
    copy(PCB / 'predict.ps1', out / 'tools/ps1/pcb_predict.ps1')
    copy(MSDD / 'train.ps1', out / 'tools/ps1/msdd_train.ps1')

    print('reference')
    copy(HACKATHON_PDF, out / 'reference/국립창원대 AI Agent 해커톤 주제 안내.pdf')
    for name, src in [('PCB_dataset', DESKTOP / 'PCB_dataset'), ('PCB_Project_v8', PCB_V8),
                      ('MSDD_v9', MSDD / 'data/msdd_raw')]:
        for f in ['data.yaml', 'README.dataset.txt', 'README.roboflow.txt']:
            copy(src / f, out / 'reference/datasets' / name / f)
    copy(PCB / 'review', out / 'reference/label_review/pcb')
    copy(MSDD / 'review', out / 'reference/label_review/msdd')

    total = sum(f.stat().st_size for f in out.rglob('*') if f.is_file())
    print(f'done: {out}  ({total / 1e6:.1f} MB, {sum(1 for f in out.rglob("*") if f.is_file())} files)')


if __name__ == '__main__':
    main()
