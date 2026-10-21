"""계산 장치 선택: 기본은 GPU, 다른 프로세스가 GPU 를 바쁘게 쓰고 있을 때만 CPU 로 물러난다.

'바쁨' 의 기준 (둘 중 하나라도 해당하면 CPU):
  - 빈 GPU 메모리가 need_mb 보다 적다 (다른 프로세스가 대부분 차지)
  - GPU 사용률이 busy_util % 이상이다 (pynvml 로 읽을 수 있을 때만)
환경변수 DEFECT_DEVICE=cpu|cuda 로 강제 지정할 수 있다.
YOLO 와 같이 한 번 올린 모델은 장치를 바꾸기 어려우므로, 모델별로 처음 쓸 때 한 번 정한다 (detect.device_for).
"""
import os


def pick_device(need_mb=500, busy_util=90):
    forced = os.environ.get('DEFECT_DEVICE', '').strip().lower()
    if forced in ('cpu', 'cuda'):
        return forced
    try:
        import torch
        if not torch.cuda.is_available():
            return 'cpu'
        free, _ = torch.cuda.mem_get_info()
        if free / 2 ** 20 < need_mb:
            return 'cpu'
        try:
            if torch.cuda.utilization() >= busy_util:
                return 'cpu'
        except Exception:  # noqa: BLE001 — pynvml 이 없으면 메모리만 본다
            pass
        return 'cuda'
    except Exception:  # noqa: BLE001 — torch 가 없거나 드라이버 문제
        return 'cpu'
