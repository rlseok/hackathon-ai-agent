"""현장 사진 사전 라벨링: 지금 모델로 검출 → YOLO 형식 라벨(.txt)을 사진 옆에 만든다.

작업자는 LabelImg / CVAT / Roboflow 에서 이 라벨을 열어 틀린 것만 고치면 된다 (처음부터 그리는 것보다 훨씬 빠르다).
정상 사진은 라벨 파일이 비어 있는 채로 저장돼 '결함 없음' 학습 샘플이 된다 (오탐 줄이기).

사용: python tools/autolabel.py <사진 폴더> --domain mobile [--conf 0.25]
결과: <사진 폴더>/labels/*.txt, classes.txt   (segmentation 모델은 폴리곤 라벨)
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent.detect import MODELS, _model  # noqa: E402

IMG_EXT = {'.jpg', '.jpeg', '.png', '.bmp'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder')
    ap.add_argument('--domain', required=True, choices=list(MODELS))
    ap.add_argument('--conf', type=float, default=0.25)
    a = ap.parse_args()
    folder = Path(a.folder)
    out = folder / 'labels'
    out.mkdir(exist_ok=True)
    model, imgsz = _model(a.domain), MODELS[a.domain][1]
    (folder / 'classes.txt').write_text('\n'.join(model.names[i] for i in sorted(model.names)) + '\n', encoding='utf-8')
    n_img = n_obj = 0
    for p in sorted(x for x in folder.iterdir() if x.suffix.lower() in IMG_EXT):
        r = model.predict(str(p), imgsz=imgsz, conf=a.conf, verbose=False)[0]
        lines = []
        if r.masks is not None:
            for c, poly in zip(r.boxes.cls, r.masks.xyn):
                if len(poly) >= 3:
                    lines.append(f'{int(c)} ' + ' '.join(f'{v:.5f}' for xy in poly for v in xy))
        else:
            for c, b in zip(r.boxes.cls, r.boxes.xywhn):
                lines.append(f'{int(c)} ' + ' '.join(f'{v:.5f}' for v in b.tolist()))
        (out / f'{p.stem}.txt').write_text('\n'.join(lines) + ('\n' if lines else ''), encoding='utf-8')
        n_img += 1
        n_obj += len(lines)
    print(f'{n_img}장 사전 라벨링, 객체 {n_obj}개 → {out}  (검토 후 tools/quick_train.py 로 재학습)')


if __name__ == '__main__':
    main()
