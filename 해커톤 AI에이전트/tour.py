"""화면 안내(투어): 처음 쓰는 사람에게 각 영역이 무엇을 하는지 단계별로 보여준다.

1. 언어 고르기 창(서버) → 고른 언어가 화면 언어가 된다.
2. 안내 자체는 tour_overlay.js 가 브라우저 안에서만 돌린다. 단계를 넘겨도 페이지를 다시 그리지 않아 끊기지 않고,
   강조 영역과 설명 카드가 같은 프레임에서 함께 움직인다 (카드는 강조 영역을 가장 덜 가리는 빈 자리로).
- 처음 열 때 한 번 자동으로 시작하고(outputs/.tour_seen_<화면>), 이후에는 상단 🧭 가이드 버튼으로 다시 본다.
  시연 모드(?demo=1)는 열 때마다 시작한다 (start_dashboard_demo.bat / start_chat_demo.bat).
- 영역은 st.container(key=...) 로 만든 'st-key-<key>' 클래스로 찾는다.
"""
import html
import json
import re
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from agent import records
from agent.i18n import LANGS
from ui import OUT, open_record, ss, t

# (설명 키, 강조할 영역 CSS 선택자 또는 None, 검사 결과가 필요한지)
STEPS = {
    'dash': [
        ('welcome', None, False),
        ('lang', '.st-key-tour_lang', False),
        ('ledger', '[data-testid="stSidebar"]', False),
        ('input', '.st-key-tour_input', False),
        ('verdict', '.st-key-tour_verdict', True),
        ('photos', '.st-key-tour_photos', True),
        ('table', '.st-key-tour_table', True),
        ('text', '.st-key-tour_text', True),
        ('decision', '.st-key-tour_decision', True),
        ('chat_dash', '.st-key-tour_chat', True),
        ('done', None, False),
    ],
    'chat': [
        ('welcome_chat', None, False),
        ('lang', '.st-key-tour_lang', False),
        ('ledger', '[data-testid="stSidebar"]', False),
        ('toolbar', '.st-key-tour_toolbar', False),
        ('chatbox', '.st-key-tour_chatbox', False),
        ('inputrow', '.st-key-tour_inputrow', False),
        ('panel', '.st-key-work_panel', True),
        ('panel_report', '.st-key-work_panel', True),
        ('panel_edit', '.st-key-work_panel', True),
        ('done_chat', None, False),
    ],
}
OVERLAY_JS = (Path(__file__).parent / 'tour_overlay.js').read_text(encoding='utf-8')


def _marker(app):
    return OUT / f'.tour_seen_{app}'


def autostart(app):
    """이 컴퓨터에서 이 화면을 처음 열었으면 언어 고르기 창부터 띄운다 (한 번만).

    시연 모드(주소 끝 ?demo=1, 바탕화면 시연 바로가기)는 페이지를 열 때마다(새로고침 포함) 처음처럼 띄운다.
    """
    if ss.get('tour_checked') != app:
        ss.tour_checked = app
        if st.query_params.get('demo') == '1':
            ss.tour_ask = app
        elif not _marker(app).exists():
            OUT.mkdir(parents=True, exist_ok=True)
            _marker(app).write_text('seen', encoding='utf-8')
            ss.tour_ask = app


def button(app, container=None):
    """상단 🧭 가이드 버튼."""
    if (container or st).button(f'🧭 {t("tour_btn")}', key='tour_btn', help=t('tour_btn_help')):
        ss.tour_ask = app
        st.rerun()


def prepare(app):
    """안내를 시작하는 실행에서, 화면을 그리기 전에 필요한 상태를 맞춘다
    (결과가 필요한 단계를 위해 최근 기록을 예시로 열고, 채팅형은 작업 패널을 연다)."""
    if ss.get('tour_launch') != app:
        return
    ss.tour_demo = False
    if ss.get('result') is None:
        rows = records.load(OUT)
        if rows:
            open_record(rows[-1])
            ss.tour_demo = True
    if app == 'chat' and ss.get('result') is not None:
        ss.panel_open = True


def _md(s):
    """간단한 마크다운(**굵게**, 줄바꿈) → HTML."""
    s = html.escape(s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
    return s.replace('\n', '<br>')


def _ask_language(app):
    @st.dialog('🌐 언어 · Ngôn ngữ · Language')
    def _dlg():
        st.markdown('안내에 사용할 언어를 고르세요.  \nChọn ngôn ngữ hướng dẫn.  \nChoose the language for this guide.')
        cols = st.columns(len(LANGS))
        for col, (code, name) in zip(cols, LANGS.items()):
            if col.button(name, key=f'tour_lang_{code}', width='stretch',
                          type='primary' if code == ss.lang else 'secondary'):
                ss.lang = code
                ss.tour_launch = app
                st.rerun()
        if st.button(f'{t("tour_skip")} ✕', key='tour_lang_skip', width='stretch'):
            st.rerun()
    _dlg()


def render(app):
    """화면을 다 그린 뒤 마지막에 부른다: 언어 고르기 창 또는 안내 시작."""
    if ss.get('tour_ask') == app:
        ss.tour_ask = None               # 창을 X 로 닫아도 다시 뜨지 않게
        _ask_language(app)
        return
    if ss.get('tour_launch') != app:
        return
    ss.tour_launch = None                # 한 번만 띄운다 (이후 화면을 다시 그려도 안내는 브라우저에서 계속됨)
    has_result = ss.get('result') is not None
    steps, first_needs = [], True
    for key, sel, needs in STEPS[app]:
        body = t(f'tour_{key}_b')
        if needs and not has_result:
            sel, body = None, body + '\n\n' + t('tour_no_result')
        elif needs and first_needs and ss.get('tour_demo'):
            body += '\n\n' + t('tour_demo_note')
        if needs:
            first_needs = False
        steps.append({'sel': sel, 'title': _md(t(f'tour_{key}_t')), 'body': _md(body)})
    cfg = {'steps': steps, 'dark': getattr(getattr(st.context, 'theme', None), 'type', 'dark') != 'light',
           'labels': {'step': t('tour_step'), 'back': t('tour_prev'), 'next': t('tour_next'),
                      'finish': t('tour_finish'), 'skip': t('tour_skip')}}
    code = OVERLAY_JS.replace('__CFG__', json.dumps(cfg, ensure_ascii=False))
    # 안내 코드는 부모 문서(실제 화면)에 넣어 실행한다 → 이 iframe 이 사라져도 안내는 계속 동작
    components.html(f"""<script>
      const s = window.parent.document.createElement('script');
      s.textContent = {json.dumps(code, ensure_ascii=False)};
      setTimeout(() => window.parent.document.body.appendChild(s), 300);
    </script>""", height=0)
