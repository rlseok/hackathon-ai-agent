"""사진 전처리: 학습 데이터와 현장 추론에 똑같이 적용해야 하는 변환 (tools/preprocess_dataset.py 와 agent.detect 가 함께 쓴다).

현재는 조명 편차를 줄이는 CLAHE (밝기 채널만 국부 대비 보정) 하나뿐이다. 검증된 도메인에서만 켠다 (detect.PREPROCESS).
"""
import cv2


def clahe(img_bgr, clip=2.0, tile=8):
    """LAB 의 L(밝기) 채널에만 CLAHE 를 적용 — 색은 유지하고 그림자·반사에 가린 국부 대비를 살린다."""
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    lab[:, :, 0] = cv2.createCLAHE(clipLimit=clip, tileGridSize=(tile, tile)).apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


METHODS = {'clahe': clahe}


def apply(name, img_bgr):
    return METHODS[name](img_bgr) if name else img_bgr
