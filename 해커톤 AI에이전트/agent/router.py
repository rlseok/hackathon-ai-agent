"""① 먼저 분류한다: 사진이 어떤 부품(pcb / msdd / mobile)인지 맞혀서 알맞은 결함 검출 모델로 보낸다.

작업자가 검사 대상을 고르지 않아도 된다. 구조: DINOv2(고정 특징 추출) + 로지스틱 회귀 분류기.
- 모든 도메인 사진을 한 데이터셋으로 합쳐 학습 (tools/build_router.py, 평가는 results/router/*.json).
- 확신이 낮거나(최대 확률 < threshold) 학습하지 않은 종류의 사진이면 accepted=False → 화면에서 작업자가 직접 고르게 한다.
- 모델 가중치·분류기는 models/router.joblib 한 파일에 들어 있어 인터넷 없이 동작한다.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from agent.device import pick_device

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / 'models/router.joblib'
_state = {}


class DomainUncertain(Exception):
    """라우터가 도메인을 확신하지 못함 — 작업자가 직접 선택해야 한다. .route 에 후보와 확률이 들어 있다."""

    def __init__(self, route):
        self.route = route
        super().__init__(f'도메인을 자동으로 정하지 못했습니다 (최선 후보 {route["domain"]} {route["confidence"]:.2f}). 직접 선택하세요.')


def available():
    """라우터 파일(분류기 + backbone 가중치)이 모두 있을 때만 True — 없으면 pipeline 이 예전처럼 pcb 로 처리한다."""
    return ARTIFACT.exists() and (ROOT / 'models/router_backbone.pt').exists()


def _load():
    if _state:
        return _state
    import joblib
    import timm
    import torch
    art = joblib.load(ARTIFACT)
    model = timm.create_model(art['backbone'], pretrained=False, num_classes=0, img_size=224)
    model.load_state_dict(torch.load(ROOT / art['backbone_weights'], map_location='cpu'))
    model.eval()
    _state.update(art=art, model=model, mean=model.pretrained_cfg['mean'], std=model.pretrained_cfg['std'])
    return _state


def _load_image(p):
    from PIL import Image
    return np.array(Image.open(p).convert('RGB').resize((224, 224), Image.BICUBIC))


def embed(paths, device=None, batch=32, model=None, mean=None, std=None, workers=8):
    """사진 목록 → 정규화된 특징 (N, D). 학습(build_router)과 추론이 같은 함수를 쓴다.

    device=None 이면 GPU 를 쓰고, GPU 가 다른 프로세스로 바쁠 때만 CPU (agent.device). 사진 읽기·축소는 여러 스레드로 미리 해서 GPU 가 기다리지 않게 한다.
    """
    import torch
    st = None if model is not None else _load()
    model = model or st['model']
    mean, std = mean or st['mean'], std or st['std']
    device = device or pick_device(need_mb=400)
    model = model.to(device)
    m = torch.tensor(mean, device=device).view(1, 3, 1, 1)
    s = torch.tensor(std, device=device).view(1, 3, 1, 1)
    out = []
    with torch.no_grad(), ThreadPoolExecutor(workers) as pool:
        batches = [paths[i:i + batch] for i in range(0, len(paths), batch)]
        pending = pool.submit(lambda b: list(map(_load_image, b)), batches[0]) if batches else None
        for k in range(len(batches)):
            ims = pending.result()
            pending = pool.submit(lambda b: list(map(_load_image, b)), batches[k + 1]) if k + 1 < len(batches) else None
            x = torch.from_numpy(np.stack(ims)).permute(0, 3, 1, 2).to(device).float() / 255
            out.append(model((x - m) / s).float().cpu())
    f = torch.cat(out)
    return torch.nn.functional.normalize(f, dim=1).numpy()


def classify_domain(paths, device=None):
    """사진 1장 또는 같은 부품의 여러 장 → {'domain', 'confidence', 'probs', 'accepted', 'threshold'}.

    여러 장이면 확률을 평균한다 (금속 부품의 여러 방향 사진). 학습하지 않은 종류면 accepted=False.
    """
    paths = [paths] if isinstance(paths, (str, Path)) else list(paths)
    st = _load()
    art = st['art']
    probs = art['clf'].predict_proba(embed(paths, device)).mean(0)
    best = int(probs.argmax())
    conf = float(probs[best])
    return {'domain': art['classes'][best], 'confidence': round(conf, 4), 'accepted': conf >= art['threshold'],
            'threshold': round(float(art['threshold']), 4),
            'probs': {c: round(float(p), 4) for c, p in zip(art['classes'], probs)}}


def resolve(paths, domain='auto'):
    """domain 이 'auto' 면 분류해서 정하고, 확신이 없으면 DomainUncertain. 직접 지정이면 그대로 (routing=None)."""
    if domain != 'auto':
        return domain, None
    route = classify_domain(paths)
    if not route['accepted']:
        raise DomainUncertain(route)
    return route['domain'], route
