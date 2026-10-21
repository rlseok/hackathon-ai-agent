"""화면(Streamlit) 점검 — 브라우저 없이 화면 코드를 실제로 돌려 본다 (streamlit.testing.AppTest).

확인
  ① app.py / app_chat.py 가 예외 없이 열린다
  ② [검사 시작] 이 하는 일 그대로: 분석 → 검사 대장 기록 → 결과 화면(판정·표·문장·작업 패널)이 예외 없이 그려진다 (자동 분류 결과 표시 포함)
  ③ 라우터가 종류를 정하지 못했을 때 '직접 고르기' 상자가 그려진다
Qwen 호출은 가짜 문장으로 바꿔 Ollama 없이 돈다. 검사 대장·보고서는 임시 폴더에만 쓴다.
(AppTest 는 format_func 를 쓰는 선택 위젯을 클릭 뒤 다시 돌릴 때 오류를 내므로, 버튼 대신 버튼이 부르는 함수를 직접 부른다.)
사용: python tools/ui_smoke_test.py      (패키지 폴더에서)
"""
import glob
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))

from streamlit.testing.v1 import AppTest  # noqa: E402

fails = []


def check(name, ok, info=''):
    print(f'[{"OK" if ok else "FAIL"}] {name} {info}')
    if not ok:
        fails.append(name)


def errors(at):
    return [str(e.value)[:200] for e in at.exception] if at.exception else []


def result_flow(root, img, out_root):
    """[검사 시작] 이후 화면: 분석 → 기록 → 결과 그리기."""
    import sys
    sys.path.insert(0, root)
    from agent import pipeline
    from smoke_test import fake_text
    pipeline.write_report_text = fake_text
    import ui
    from ui import chat_panel, init_state, result_body, ss, t, verdict_header
    init_state()
    r = pipeline.register_pending(pipeline.analyze(img, 'auto', lang='ko', out_root=out_root), out_root)
    ui._adopt(r)
    verdict_header(r)
    result_body(r)
    chat_panel(r)
    ss.smoke_domain = r['detection']['domain']
    ss.smoke_routing = bool(r.get('routing'))


def unsure_flow(root, img):
    """라우터가 확신하지 못한 경우: ss.unsure 를 채우고 선택 상자를 그린다."""
    import sys
    sys.path.insert(0, root)
    from agent import pipeline
    from agent.router import DomainUncertain
    import ui
    from ui import init_state, ss, start, unsure_box

    def boom(*a, **k):
        raise DomainUncertain({'domain': 'pcb', 'confidence': 0.6, 'probs': {'pcb': 0.6, 'msdd': 0.3, 'mobile': 0.1}, 'accepted': False})
    pipeline.analyze = boom
    ui.analyze = boom
    init_state()
    r = start([img], 'auto', {})
    ss.smoke_start_returned_none = r is None
    unsure_box()


tmp = Path(tempfile.mkdtemp(prefix='ui_smoke_'))
imgs = {d: sorted(glob.glob(str(ROOT / f'results/{d}/showcase/*/originals/images/01_*')))[:1] for d in ('pcb', 'msdd')}
img = next((v[0] for v in imgs.values() if v), None)

for app in ('app.py', 'app_chat.py'):
    at = AppTest.from_file(str(ROOT / app), default_timeout=900).run()
    check(f'{app}: 열림', not at.exception, str(errors(at)))

if img:
    at = AppTest.from_function(result_flow, args=(str(ROOT), img, tmp), default_timeout=900).run()
    check('결과 화면 그리기 (분석→기록→판정·표·문장·대화)', not at.exception,
          str(errors(at)) if at.exception else f'도메인 {at.session_state["smoke_domain"]}, 자동분류 표시={at.session_state["smoke_routing"]}')
    at = AppTest.from_function(unsure_flow, args=(str(ROOT), img), default_timeout=300).run()
    ok = not at.exception and at.session_state['smoke_start_returned_none'] and bool(at.session_state['unsure'])
    check('불확실 → 직접 고르기 상자', ok and any('route' in (w.key or '') or 'unsure' in (w.key or '') for w in at.radio) or ok,
          str(errors(at)) if at.exception else f'라디오 {len(at.radio)}개, 경고 {len(at.warning)}개')
else:
    check('예시 사진 찾음', False)

shutil.rmtree(tmp, ignore_errors=True)
print(f'\n{"전부 통과" if not fails else "실패: " + str(fails)}')
sys.exit(1 if fails else 0)
