"""작업자 확인 화면 — 대시보드형 (Streamlit).

본문 상단 [검사 입력] → 검사 결과(사진·결함 표·문장·처리) + 오른쪽 대화창, 좌측 사이드바 검사 대장.
채팅이 가운데 오는 화면은 app_chat.py.

실행: streamlit run app.py   (패키지 폴더에서, 가상환경 활성화 상태로, Ollama 실행 중)
"""
import streamlit as st

import tour
from ui import (ICONS, INBOX, IMG_TYPES, ROOT, app_chrome, chat_panel, domain_input, example_picker, header,
                inbox_summary, init_state, keep, ledger_sidebar, meta_inputs, result_body, run_inbox, save_uploads,
                scan_inbox, ss, start, t, verdict_header)

st.set_page_config(page_title='Defect Agent', page_icon=str(ICONS['dash']), layout='wide')
app_chrome('dash')
init_state()
tour.autostart('dash')                   # 처음 열면 화면 안내 시작
tour.prepare('dash')

header(tour_app='dash')
ledger_sidebar()

# ── 검사 입력 ─────────────────────────────────────────────────────
with st.container(key='tour_input'), st.expander(f'📷 {t("input")}', expanded=ss.result is None):
    c1, c2, c3 = st.columns([1, 1.3, 2.2])
    with c1:
        domain = domain_input()
    with c2:
        mode = keep('mode', ['example', 'upload', 'inbox'], t('source'), radio=True, horizontal=True,
                    format_func=lambda m: t(f'source_{m}'))
    with c3:
        meta = meta_inputs()

    paths, files = [], None
    if mode == 'example':
        paths = example_picker(domain)
    elif mode == 'upload':
        files = st.file_uploader(t('upload_help'), type=IMG_TYPES, accept_multiple_files=True)
        if files:
            st.caption(t('n_files', n=len(files)))
    else:
        found = scan_inbox()
        st.caption(t('inbox_help', path=INBOX.relative_to(ROOT).as_posix()))
        st.write(' · '.join(f'{t(f"domain_{d}")}: {len(v)}' for d, v in found.items()) or t('inbox_empty'))
        if st.button(t('inbox_run'), type='primary', disabled=not any(found.values())):
            ss.inbox_msg = inbox_summary(run_inbox(meta))
            st.rerun()
        if ss.get('inbox_msg'):
            st.success(f'{ss.inbox_msg} — {t("inbox_next")}')
    if mode != 'inbox' and st.button(t('run'), type='primary', disabled=mode == 'upload' and not files):
        start(paths if mode == 'example' else save_uploads(files), domain, meta)
        st.rerun()

# ── 검사 결과 ─────────────────────────────────────────────────────
r = ss.result
if r is None:
    st.info(t('guide'))
    tour.render('dash')
    st.stop()

verdict_header(r)
main, side = st.columns([3, 2], gap='large')
with main:
    result_body(r)
with side:
    chat_panel(r)
tour.render('dash')
