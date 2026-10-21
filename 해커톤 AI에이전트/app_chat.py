"""작업자 확인 화면 — 채팅형 (Streamlit).

가운데 대화창에서 검사를 시작하고(📎 사진 첨부 / 📷 예시 / 📥 대기함) 결과는 대화에 카드로 남는다.
오른쪽 작업 패널은 좌측 사이드바처럼 화면 오른쪽에 붙어 따로 스크롤되며 열고 닫을 수 있다.
  - [보고서] 탭: 저장될 보고서 그대로 → 고칠 문장을 드래그해 복사, 대화창에 붙여 넣고 "이렇게 고쳐줘"
  - [편집·확정] 탭: 결함 표 수정, 문장 편집, 미리보기·저장, 오탐 기각 (판정은 여기서만 바뀐다)
수정 요청은 Qwen 이 바꿀 문장만 제안하고, [적용]을 눌러야 반영된다.

실행: streamlit run app_chat.py --server.port 8503   (대시보드형 app.py 와 동시에 띄울 때 포트를 다르게)
"""
import streamlit as st

import tour
from agent import records
from agent.chat import apply_edit, looks_like_edit, propose_edit
from agent.pipeline import load_result
from ui import (DOT, ICONS, IMG_TYPES, OUT, _adopt, app_chrome, domain_input, example_picker, header, inbox_summary, init_state,
                ledger_sidebar, meta_inputs, open_record, persist, quick_questions, right_panel_css, run_inbox,
                save_uploads, scan_inbox, ss, start, stream_answer, sync_result, t, type_name, verdict_name, work_panel)

st.set_page_config(page_title='Defect Agent · Chat', page_icon=str(ICONS['chat']), layout='wide')
app_chrome('chat')
init_state(log=[], panel_open=False, panel_width='normal')   # log: 대화 [{role, content, files?, card?, proposal?}]
sync_result()


def card_of(r):
    det, sit = r['detection'], r['situation']
    rep = sit.get('representative')
    kb = {k['type']: k for k in r['knowledge']}
    return {'name': r['name'], 'verdict': det['verdict'], 'image': det.get('marked_image') or det['image'],
            'rep': rep, 'rep_kb': kb.get(rep), 'n': len(det['defects']), 'work': str(r['work'])}


def say(role, content, **extra):
    ss.log.append({'role': role, 'content': content, **extra})


def inspect(paths, domain, meta, user_text):
    say('user', user_text, files=[str(p) for p in paths])
    r = start(paths, domain, meta)
    ss.panel_open = True
    say('assistant', f'{r["text"].get("summary", "")}\n\n{t("card_hint_panel")}', card=card_of(r))


def open_card(card):
    entry = next((e for e in records.load(OUT) if e['id'] == card['name']), None)
    if entry:
        open_record(entry)
    else:
        from pathlib import Path
        _adopt(load_result(Path(card['work']) / f'{card["name"]}_result.json'))
    ss.panel_open = True


def render_card(card, key):
    c1, c2 = st.columns([1, 2], vertical_alignment='center')
    c1.image(card['image'], width=150)
    rep = type_name(card['rep'], card['rep_kb'], ss.lang) if card['rep'] else '-'
    c2.markdown(f'{DOT[card["verdict"]]} **{verdict_name(card["verdict"], ss.lang)}** · {rep} · '
                f'{t("n_items_ui", n=card["n"])}')
    is_open = ss.panel_open and ss.result is not None and ss.result['name'] == card['name']
    if c2.button(t('open_panel') if not is_open else t('opened_panel'), key=key, disabled=is_open,
                 type='secondary' if is_open else 'primary'):
        open_card(card)
        st.rerun()


def render_proposal(m, key):
    """수정 제안: 바뀌는 부분 전/후 + [적용] [취소]."""
    p = m['proposal']
    labels = {'summary': t('summary'), 'cause_text': t('causes'), 'action_immediate': t('act_now'),
              'action_prevent': t('act_prevent')}
    for k, new in p['changes'].items():
        if k == 'defects':
            for d in new:
                st.markdown(f'**{t("feature")} — {d["type"]}**')
                st.markdown(f'> {d["description"]}')
        else:
            st.markdown(f'**{labels.get(k, k)}**')
            if p['before'].get(k):
                st.markdown(f'<span style="color:#999;text-decoration:line-through">{p["before"][k]}</span>',
                            unsafe_allow_html=True)
            st.markdown(f'> {new}')
    if m.get('applied'):
        st.caption(t('edit_applied'))
    elif m.get('dismissed'):
        st.caption(t('edit_dismissed'))
    else:
        a, b = st.columns(2)
        if a.button(t('edit_apply'), key=f'ap_{key}', type='primary', width='stretch'):
            if ss.result and ss.result['name'] == p['name']:
                persist(apply_edit(ss.result, p['changes']))
                m['applied'] = True
                ss.panel_open = True
            st.rerun()
        if b.button(t('edit_cancel'), key=f'dc_{key}', width='stretch'):
            m['dismissed'] = True
            st.rerun()


GUIDE = [('g_verdict', 'ex_why'), ('g_defects', 'ex_where'), ('g_cause', 'ex_cause'), ('g_action', 'ex_check'),
         ('g_lang', 'ex_lang'), ('g_edit', 'ex_edit')]


def ask_guide(r, where):
    """질문 안내: 무엇을 물어볼 수 있는지 + 누르면 바로 보내지는 예시 질문. 누른 예시를 돌려준다."""
    rep = r['situation'].get('representative')
    kb = {k['type']: k for k in r['knowledge']}
    name = type_name(rep, kb.get(rep), ss.lang) if rep else t('g_this_defect')
    st.markdown(f'**💬 {t("guide_title")}**')
    st.caption(t('guide_intro'))
    picked = None
    for i, (label, ex) in enumerate(GUIDE):
        c1, c2 = st.columns([1, 2.6], vertical_alignment='center')
        c1.markdown(t(label))
        q = t(ex, name=name)
        if c2.button(q, key=f'gx_{where}_{i}', width='stretch'):
            picked = q
    st.caption(t('guide_cannot'))
    return picked


def on_ledger_open(e):
    ss.panel_open = True
    say('assistant', t('opened_from_ledger'), card=card_of(ss.result))


def open_from_link():
    """실시간 화면의 [채팅에서 열기] 링크(?open=<기록 id>&lang=..) → 그 기록을 오른쪽 작업 패널에 연다 (보고서 문장은 열 때 작성)."""
    rid = st.query_params.get('open')
    if not rid:
        return False
    if st.query_params.get('lang') in ('ko', 'vi', 'en'):
        ss.lang = st.query_params['lang']
    for k in ('open', 'lang'):              # 새로고침해도 다시 열지 않게
        st.query_params.pop(k, None)
    entry = next((e for e in records.load(OUT) if e['id'] == rid), None)
    if entry is None:                        # 아직 대장에 기록되기 전 (판정 직후 아주 잠깐)
        say('assistant', t('live_not_found', id=rid))
        return True
    open_record(entry)
    ss.panel_open = True
    say('assistant', t('opened_from_live'), card=card_of(ss.result))
    return True


if not open_from_link():                 # 링크로 온 경우에는 화면 안내를 띄우지 않는다
    tour.autostart('chat')               # 처음 열면 화면 안내 시작
tour.prepare('chat')
right_panel_css(ss.panel_open, ss.panel_width)
header(tour_app='chat')
ledger_sidebar(on_open=on_ledger_open)

# ── 가운데: 대화 ───────────────────────────────────────────────────
narrow = ss.panel_open                   # 작업 패널이 열리면 가운데가 좁아지므로 버튼을 아이콘 위주로
tb1, tb2, tb3, tb4 = st.container(key='tour_toolbar').columns(4)
with tb1.popover(f'⚙ {t("domain_" + ss.get("sel_domain", "pcb"))}' + ('' if narrow else f' · {t("part_short")}'),
                 width='stretch', help=t('part_short')):
    domain = domain_input()
    meta = meta_inputs()
def close_example():                     # [검사 시작]을 누르면 예제 창을 닫는다 (콜백이라 위젯 상태를 바꿀 수 있다)
    ss.ex_pop = False


with tb2.popover('📷' if narrow else f'📷 {t("source_example")}', width='stretch', help=t('source_example'),
                 key='ex_pop', on_change=lambda: None):
    ex_paths = example_picker(domain)
    if st.button(t('run'), type='primary', key='ex_run', on_click=close_example):
        inspect(ex_paths, domain, meta, t('chat_example_msg', name=ex_paths[0].name[:40], n=len(ex_paths)))
        st.rerun()
n_inbox = sum(len(v) for v in scan_inbox().values())
if tb3.button(f'📥 ({n_inbox})' if narrow else f'📥 {t("inbox_run")} ({n_inbox})', disabled=not n_inbox,
              width='stretch', help=t('inbox_run')):
    say('user', t('inbox_run'))
    res = run_inbox(meta)
    say('assistant', f'{inbox_summary(res)}\n\n{t("inbox_next_chat")}')
    for x in res:
        if x['detection']['verdict'] != 'normal':
            say('assistant', x['text'].get('summary', ''), card=card_of(x))
    st.rerun()
if tb4.button('🛠 ▶' if narrow else f'🛠 {t("panel_show")}', width='stretch',
              help=t('panel_hide') if ss.panel_open else t('panel_show'),
              type='secondary' if ss.panel_open else 'primary'):
    ss.panel_open = not ss.panel_open
    st.rerun()

box = st.container(height=560, key='tour_chatbox')
with box:
    if not ss.log:
        st.chat_message('assistant').markdown(t('chat_welcome_panel'))
    for i, m in enumerate(ss.log):
        with st.chat_message(m['role']):
            if m.get('files'):
                st.image(m['files'], width=90)
            if m['content']:
                st.markdown(m['content'])
            if m.get('card'):
                render_card(m['card'], key=f'card_{i}')
            if m.get('proposal'):
                render_proposal(m, key=i)

gq = None
# 질문 안내 상자: 새 검사가 열리고 아직 질문하지 않았으면 입력창 위에 자동으로 보인다
guide_shown = bool(ss.result and not ss.get('guide_off') and ss.get('guide_seen') != ss.result['name'])
if guide_shown:
    with st.container(border=True):
        gq = ask_guide(ss.result, 'inline')
        d1, d2 = st.columns(2)
        if d1.button(t('guide_close'), key='guide_close', width='stretch'):
            ss.guide_seen = ss.result['name']
            st.rerun()
        if d2.button(t('guide_never'), key='guide_never', width='stretch'):
            ss.guide_off = True
            st.rerun()

# 입력창은 화면 하단 고정이 아니라 대화창 바로 아래에 둔다
# (하단 고정이면 Streamlit 이 페이지를 계속 맨 아래로 붙여, 화면 안내가 위쪽 영역을 보여줄 수 없다)
inrow = st.container(key='tour_inputrow')
msg = inrow.chat_input(t('chat_ph_panel'), accept_file='multiple', file_type=IMG_TYPES)
qcol, hcol, ecol = inrow.columns([1.3, 0.5, 1] if narrow else [4, 0.6, 1.3], vertical_alignment='center')
with qcol:
    qq = quick_questions(compact=narrow) if ss.result else None
with hcol.popover('❓', help=t('guide_title'), disabled=not ss.result):
    if ss.result:
        gq = ask_guide(ss.result, 'pop') or gq
ss.edit_mode = ecol.toggle(t('edit_mode'), value=ss.get('edit_mode', False), disabled=not ss.result,
                           help=t('edit_mode_help'))
if msg and msg.files:                    # 사진 첨부 → 검사 (판정은 코드가 고정 절차로)
    inspect(save_uploads(msg.files), domain, meta, msg.text or t('chat_inspect_default'))
    st.rerun()
q = (msg.text if msg else None) or qq or gq
if q:
    say('user', q)
    if ss.result:
        ss.guide_seen = ss.result['name']        # 질문을 시작했으면 안내 상자는 접는다
    if ss.result and (ss.edit_mode or looks_like_edit(q)):         # 수정 요청 → 제안 → [적용]
        with box, st.spinner(t('edit_thinking')):
            try:
                p = propose_edit(q, ss.result, ss.lang)
            except Exception as e:  # noqa: BLE001 — Ollama 미실행 등
                p = {'changes': {}, 'note': f'{t("chat_error")} ({e})'}
        if p['changes']:
            before = {k: ss.result['text'].get(k, '') for k in p['changes'] if k != 'defects'}
            say('assistant', p['note'] or t('edit_proposed'),
                proposal={'name': ss.result['name'], 'changes': p['changes'], 'before': before})
        else:
            say('assistant', p['note'] or t('edit_none'))
        st.rerun()
    with box:                            # 질문 → Qwen (지금 열린 검사 기준)
        st.chat_message('user').markdown(q)
        with st.chat_message('assistant'):
            if ss.result:
                ans = stream_answer([{'role': m['role'], 'content': m['content']} for m in ss.log if m['content']],
                                    ss.result)
            else:
                ans = t('chat_no_result')
                st.markdown(ans)
    say('assistant', ans)
    if guide_shown:                      # 첫 질문을 했으니 안내 상자를 접은 화면으로
        st.rerun()

# ── 오른쪽: 작업 패널 (고정, 따로 스크롤) ────────────────────────────
if ss.panel_open:
    work_panel(ss.result)

tour.render('chat')                      # 화면 안내 (켜져 있을 때만)
