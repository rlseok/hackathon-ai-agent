"""노트북 설치 확인 스크립트.

1) Python / 패키지  2) YOLO 모델 2종 로드 + 우수 사례 원본으로 시험 추론  3) Ollama + Qwen 응답
사용: python check_setup.py  (패키지 폴더에서, 가상환경 활성화 상태로)
"""
import importlib
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'check_output'
OLLAMA = 'http://localhost:11434'
ok_all = True


def report(ok, msg):
    global ok_all
    ok_all &= ok
    print(f'  [{"OK" if ok else "FAIL"}] {msg}')


def check_python():
    print('1. Python / 패키지')
    v = sys.version_info
    report(v >= (3, 10), f'Python {v.major}.{v.minor}.{v.micro}')
    for mod in ['ultralytics', 'torch', 'cv2', 'yaml', 'ollama', 'streamlit', 'docx']:
        try:
            m = importlib.import_module(mod)
            report(True, f'{mod} {getattr(m, "__version__", "")}')
        except ImportError:
            report(False, f'{mod} 없음 → pip install -r requirements.txt')
    try:
        import torch
        print(f'  [INFO] GPU 사용 가능: {torch.cuda.is_available()}')
    except ImportError:
        pass


def check_models():
    print('2. YOLO 모델')
    try:
        from ultralytics import YOLO
    except ImportError:
        report(False, 'ultralytics 가 없어 건너뜀')
        return
    OUT.mkdir(exist_ok=True)
    tests = [
        ('pcb_v2_yolo11s.pt', 640, ROOT / 'results/pcb/showcase', False),
        ('msdd_v1_yolo11s_seg.pt', 512, ROOT / 'results/msdd/showcase', False),
        # 휴대폰 표면 (Izumi 학습) — 데이터 라이선스 확인 전이라 공개 저장소에는 없을 수 있다 → 없으면 건너뜀
        ('mobile_surface_yolo11s_seg.pt', 512, ROOT / 'results/mobile/showcase', True),
    ]
    for name, imgsz, showcase, optional in tests:
        if optional and not (ROOT / 'models' / name).exists():
            print(f'  [INFO] {name} 없음 — 휴대폰 표면 검사는 건너뜀 (모델 파일을 models/ 에 넣으면 사용 가능)')
            continue
        try:
            model = YOLO(str(ROOT / 'models' / name))
            report(True, f'{name} 로드 (클래스 {len(model.names)}개: {", ".join(model.names.values())})')
        except Exception as e:  # noqa: BLE001
            report(False, f'{name} 로드 실패: {e}')
            continue
        imgs = sorted(showcase.glob('*/originals/images/01_*'))
        if not imgs:
            if optional:
                print(f'  [INFO] {showcase.relative_to(ROOT)} 에 시험 이미지가 없어 추론 시험은 건너뜀')
            else:
                report(False, f'{showcase} 에 시험 이미지가 없음')
            continue
        for img in imgs:
            r = model.predict(str(img), imgsz=imgsz, conf=0.25, verbose=False)[0]
            found = [model.names[int(c)] for c in r.boxes.cls]
            case = img.parents[2].name
            r.save(filename=str(OUT / f'{Path(name).stem}__{case}.jpg'))
            print(f'  [INFO] {case:16s} → 검출 {len(found)}개 {sorted(set(found))}')
        report(True, f'{name} 시험 추론 완료 → {OUT.name}/ 에 결과 저장')


def check_ollama():
    print('3. Ollama / Qwen')
    try:
        with urllib.request.urlopen(f'{OLLAMA}/api/tags', timeout=5) as resp:
            models = [m['name'] for m in json.load(resp)['models']]
        report(True, f'Ollama 서버 연결, 모델: {models or "(없음)"}')
    except Exception as e:  # noqa: BLE001
        report(False, f'Ollama 연결 실패 ({e}) → Ollama 실행 여부 확인')
        return
    want = os.environ.get('DEFECT_LLM', 'qwen3:8b')        # 에이전트가 실제로 쓰는 모델을 먼저 시험
    qwen = sorted((m for m in models if m.startswith('qwen')), key=lambda m: m.split(':')[0] != want.split(':')[0])
    if not qwen:
        report(False, 'Qwen 모델 없음 → ollama pull qwen3:8b')
        return
    body = json.dumps({'model': qwen[0], 'stream': False, 'think': False,
                       'prompt': 'PCB 단선 불량의 원인을 한 문장으로 답하라.'}).encode()
    req = urllib.request.Request(f'{OLLAMA}/api/generate', body, {'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            ans = json.load(resp).get('response', '').strip()
        report(bool(ans), f'{qwen[0]} 응답: {ans[:120]}')
    except Exception as e:  # noqa: BLE001
        report(False, f'{qwen[0]} 응답 실패: {e}')


if __name__ == '__main__':
    check_python()
    check_models()
    check_ollama()
    print('\n결과:', '모두 정상 — 에이전트 개발을 시작할 수 있습니다.' if ok_all else '실패 항목을 docs/04 문제 해결 표에서 확인하세요.')
