"""분배 에이전트 (혼합 라인): 벨트 위 제품이 어떤 종류(pcb / msdd / mobile)인지 가려 맞는 모델·지식으로 보낸다.

규칙 기반이다. Izumi 의 학습형 라우터(DINOv2 + 로지스틱 회귀, feat/auto-router-rag-data-audit)는 timm·scikit-learn·joblib 과
backbone 가중치가 더 필요해서, 새로 받지 않는 지금 환경에서는 쓰지 않았다 (docs/06 30절).
카메라 하나·벨트 하나라 제품의 겉모양 차이가 뚜렷하다:
  - 액정(휴대폰 표면)  가로로 긴 16:9                 → 가로세로비
  - PCB               초록 기판                        → 초록 비율
  - 금속 부품          검은 배경 위 원형 부품            → 어두운 비율
영상 서버(live/server.py --line mixed)가 '벨트 색과 다른 영역'으로 찾은 제품 상자를 그대로 넘긴다.
"""
import numpy as np

SIZES = {'pcb': (640, 640), 'msdd': (512, 512), 'mobile': (960, 540)}    # 제품(센싱 구역) 크기 — 라인 영상과 같다
# 규칙 기준값 — 혼합 영상 90개의 분포(docs/06 30절)에서 정함: 가로세로비 PCB·금속 1.00 / 액정 1.73~1.94,
# 초록 PCB 0.74~0.91 / 그 밖 0.00, 어두운 비율 금속 0.21~0.55 / PCB 0.02~0.14 (액정도 어둡지만 가로세로비가 먼저 가린다)
WIDE, GREEN, DARK = 1.4, 0.15, 0.15


def features(region, w, h):
    """region = 제품 상자 안 화면 (BGR, 줄인 화면이어도 됨), w·h = 원래 화면에서의 상자 크기 px."""
    px = region.reshape(-1, 3).astype(np.int16)
    b, g, r = px[:, 0], px[:, 1], px[:, 2]
    return {'w': int(w), 'h': int(h), 'aspect': round(w / max(h, 1), 2),
            'green': round(float(((g - np.maximum(r, b)) > 25).mean()), 3),
            'dark': round(float((px.max(axis=1) < 50).mean()), 3)}


def route(region, w, h):
    """→ {'domain', 'rule', 'features'}. 규칙에 하나도 안 걸리면 크기가 가장 가까운 종류 (rule='size')."""
    f = features(region, w, h)
    if f['aspect'] >= WIDE:
        dom, rule = 'mobile', 'wide'
    elif f['green'] >= GREEN:
        dom, rule = 'pcb', 'green'
    elif f['dark'] >= DARK:
        dom, rule = 'msdd', 'dark'
    else:
        dom = min(SIZES, key=lambda d: abs(SIZES[d][0] - w) + abs(SIZES[d][1] - h))
        rule = 'size'
    return {'domain': dom, 'rule': rule, 'features': f}
