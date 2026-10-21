"""두 화면(app.py 대시보드형, app_chat.py 채팅형)이 함께 쓰는 Streamlit 부품.

상태(st.session_state): lang, result(지금 열린 검사), done(처리 완료된 결과), sel_*(입력 선택값)
"""
import json
import time
from pathlib import Path

import pandas as pd
import streamlit as st

from agent import records
from agent.chat import chat_stream
from agent.router import DomainUncertain
from agent.history import answer as history_answer, looks_like_history
from agent.detect import ROOT, _model, parse_view
from agent.i18n import (LANGS, PROCESS, STATUS, T, level_name, pos_text, process_name, reason_text, type_name,
                        verdict_name)
from agent.pipeline import (INBOX, OUT, analyze, finalize, load_result, process_inbox, refresh, register_pending,
                            reject_false_positive, save_result, scan_inbox)
from agent.report import build_report
from loading_icon import loading_data_uri

SHOWCASE = {'pcb': ROOT / 'results/pcb/showcase', 'msdd': ROOT / 'results/msdd/showcase'}
# 우수 사례 폴더가 없는 도메인은 학습 데이터의 test 사진 일부를 예시로 쓴다 (데이터 폴더가 있을 때만)
SAMPLES = {'mobile': ROOT.parent / 'data/mobile_surface/images/test'}
DOMAINS = ['auto', 'pcb', 'msdd', 'mobile']
BADGE = {'normal': '#2E7D32', 'review': '#E68A00', 'reject': '#C62828'}
DOT = {'normal': '🟢', 'review': '🟠', 'reject': '🔴'}
IMG_TYPES = ['jpg', 'jpeg', 'png', 'bmp']
ss = st.session_state


ICONS = {'dash': ROOT / 'assets/demo_dashboard.png', 'chat': ROOT / 'assets/demo_chat.png'}

# 처리 중 표시: Streamlit 기본(달리기·수영 등 스포츠 그림이 바뀜) 대신
# 맞물려 도는 큰·작은 톱니바퀴 + 둘레를 도는 원형 버퍼 (loading_icon.py, SVG 자체 애니메이션)
BUSY_CSS = f"""<style>
[data-testid="stStatusWidgetRunningManIcon"] {{display:none !important;}}
[data-testid="stStatusWidgetRunningIcon"] {{display:flex; align-items:center; padding-right:4px;}}
[data-testid="stStatusWidgetRunningIcon"]::before {{content:""; width:34px; height:34px;
    background:url("{loading_data_uri()}") center/contain no-repeat;}}
</style>"""


def app_chrome(app):
    """두 화면 공통 꾸미기: 왼쪽 위 로고(바로가기와 같은 아이콘) + 처리 중 표시(톱니바퀴·버퍼링)."""
    st.logo(str(ICONS[app]), size='large')
    st.html(BUSY_CSS)


def init_state(**extra):
    for k, v in {'lang': 'ko', 'result': None, 'done': None, 'chat': [], **extra}.items():
        ss.setdefault(k, v)


def t(key, **kw):
    return T(key, ss.lang, **kw)


# ── 입력 도우미 ───────────────────────────────────────────────────
@st.cache_data
def examples(domain):
    """케이스 → 예시 사진 목록. 'auto' 는 모든 도메인 예시를 합친다 (종류를 모르는 상태로 시작)."""
    if domain == 'auto':
        return {f'{d}/{k}': v for d in SHOWCASE.keys() | SAMPLES.keys() for k, v in examples(d).items()}
    if domain in SHOWCASE:
        return {p.name.split('_', 1)[1]: sorted((p / 'originals/images').glob('*.jpg'))
                for p in sorted(SHOWCASE[domain].iterdir()) if (p / 'originals/images').is_dir()}
    folder = SAMPLES.get(domain)
    return {'sample': sorted(folder.glob('*.jpg'))[:12]} if folder and folder.is_dir() else {}


def same_part_images(img):
    """금속: 같은 부품의 다른 방향 사진 (우수 사례 전체에서, 방향별 1장)."""
    pid, _ = parse_view(img)
    views = {}
    for p in sorted(SHOWCASE['msdd'].glob('*/originals/images/*.jpg')):
        q, v = parse_view(p)
        if q == pid:
            views.setdefault(v, p)
    return list(views.values())


def save_uploads(files):
    d = OUT / 'uploads' / time.strftime('%Y%m%d_%H%M%S')
    d.mkdir(parents=True, exist_ok=True)
    paths = []
    for f in files:
        p = d / f.name
        p.write_bytes(f.getbuffer())
        paths.append(p)
    return paths


def keep(name, options, label, **kw):
    """언어를 바꾸면 라벨이 바뀌어 위젯이 새로 만들어지므로, 선택값은 세션에 따로 보관해 다시 채운다."""
    options = list(options)
    cur = ss.get(f'sel_{name}')
    idx = options.index(cur) if cur in options else 0
    widget = st.radio if kw.pop('radio', False) else st.selectbox
    ss[f'sel_{name}'] = widget(label, options, index=idx, **kw)
    return ss[f'sel_{name}']


def verdict_key(e):
    return e.get('verdict') or {'정상': 'normal', '의심': 'review', '이상': 'reject'}.get(e.get('판정'), 'normal')


# ── 결과 저장·동기화 (디스크) ──────────────────────────────────────
# 고친 내용은 바로 <검사>_result.json 에 저장한다 (화면을 닫아도 이어서 볼 수 있게).
# 같은 검사를 다른 탭에서 고쳤으면, 바뀐 것을 보고 다시 읽는다.
def result_file(r):
    return Path(r['work']) / f'{r["name"]}_result.json'


def _mtime(p):
    try:
        return Path(p).stat().st_mtime_ns
    except OSError:
        return None


def _snapshot(r):
    return json.dumps([r['text'], r['detection']['defects'], r['detection']['verdict']], ensure_ascii=False, sort_keys=True)


def _adopt(r):
    """세션의 '지금 열린 검사'로 삼고 디스크 상태를 기억한다."""
    ss.result = r
    ss.done = r if r.get('status') and r['status'] != 'pending' else None
    ss.seen_mtime = _mtime(result_file(r))
    ss.saved_snapshot = _snapshot(r)


def persist(r):
    """결과를 디스크에 저장 (다른 창이 이 변경을 읽어 간다)."""
    save_result(r)
    ss.seen_mtime = _mtime(result_file(r))
    ss.saved_snapshot = _snapshot(r)


def autosave(r):
    """작업자가 고친 내용(결함 표·문장)을 바로 저장 → 화면을 닫아도, 다른 창에서도 이어서 볼 수 있다."""
    if r and _snapshot(r) != ss.get('saved_snapshot'):
        persist(r)


def sync_result():
    """다른 창이 결과를 고쳤으면 다시 읽는다. 바뀌었으면 True."""
    r = ss.get('result')
    if not r:
        return False
    m = _mtime(result_file(r))
    if m and m != ss.get('seen_mtime'):
        _adopt(load_result(result_file(r)))
        return True
    return False


# ── 동작 ─────────────────────────────────────────────────────────
def start(paths, domain, meta):
    """분석 → 검사 대장에 '작업자 확인 대기'로 기록 → 지금 열린 검사로.

    domain='auto' 인데 라우터가 확신하지 못하면 None 을 돌려주고 ss.unsure 에 후보를 남긴다 (unsure_box 가 작업자에게 묻는다).
    """
    try:
        with st.spinner(t('analyzing')):
            r = register_pending(analyze(paths if len(paths) > 1 else paths[0], domain, lang=ss.lang, meta=meta))
    except DomainUncertain as e:
        ss.unsure = {'paths': [str(p) for p in paths], 'route': e.route, 'meta': meta}
        return None
    ss.unsure = None
    _adopt(r)
    ss.chat = []
    return r


def unsure_box():
    """라우터가 종류를 정하지 못했을 때: 후보 확률을 보여주고 작업자가 직접 고르게 한다. 고르면 그 종류로 검사."""
    u = ss.get('unsure')
    if not u:
        return
    probs = u['route']['probs']
    best = max(probs, key=probs.get)
    with st.container(border=True):
        st.warning(t('route_unsure', best=t(f'domain_{best}'), conf=f'{probs[best]:.2f}'))
        order = sorted(probs, key=probs.get, reverse=True)
        pick = st.radio(t('domain'), order, horizontal=True, key='unsure_pick',
                        format_func=lambda d: f'{t("domain_" + d)} ({probs[d]:.2f})')
        if st.button(t('route_pick'), type='primary', key='unsure_go'):
            ss.sel_domain = pick
            start(u['paths'], pick, u['meta'])
            st.rerun()


def open_record(entry):
    """검사 대장의 기록 열기. 확인 대기면 이어서 확인, 처리 끝난 건이면 결과·보고서 보기."""
    r = load_result(OUT / entry['result_json'])
    if entry['status'] != 'pending':
        r['status'] = entry['status']
    _adopt(r)
    ss.chat = []


def run_inbox(meta, progress_box=None):
    bar = (progress_box or st).progress(0.0)
    res = process_inbox(ss.lang, meta, progress=lambda i, n, s: bar.progress(i / max(n, 1), text=s[:40]))
    ss.sel_flt = 'pending'           # 사이드바 대장을 '확인 대기'로
    return res


def inbox_summary(res):
    return t('inbox_done', n=len(res), r=sum(x['detection']['verdict'] == 'reject' for x in res),
             s=sum(x['detection']['verdict'] == 'review' for x in res),
             o=sum(x['detection']['verdict'] == 'normal' for x in res))


# ── 화면 부품 ─────────────────────────────────────────────────────
def header(tour_app=None):
    """제목 + 우측 상단 🧭 가이드 버튼 · 언어 선택."""
    top_l, top_g, top_r = st.columns([5, 0.9, 1], vertical_alignment='center')
    top_l.title(t('title'))
    if tour_app:
        import tour
        tour.button(tour_app, top_g)
    with top_r.container(key='tour_lang'):
        with st.popover(f'🌐 {LANGS[ss.lang]}', width='content'):
            choice = st.radio('Language', list(LANGS), format_func=LANGS.get, index=list(LANGS).index(ss.lang),
                              label_visibility='collapsed')
            if choice != ss.lang:
                ss.lang = choice
                st.rerun()


def meta_inputs():
    """품번 · 공정 · 로트 (현재 컨테이너에 3칸)."""
    m1, m2, m3 = st.columns(3)
    ss.sel_part_no = m1.text_input(t('m_part_no'), ss.get('sel_part_no', ''), placeholder='A-1234')
    with m2:
        process = keep('process', PROCESS, t('m_process'), format_func=lambda c: process_name(c, ss.lang))
    ss.sel_lot = m3.text_input(t('m_lot'), ss.get('sel_lot', ''), placeholder='L2026-1016-01')
    return {'part_no': ss.sel_part_no.strip(), 'process': process, 'lot': ss.sel_lot.strip()}


def domain_input():
    return keep('domain', DOMAINS, t('domain'), radio=True, horizontal=True,
                format_func=lambda d: t(f'domain_{d}'))


def example_picker(domain):
    """예시 사진 선택 → 사진 경로 목록."""
    ex = examples(domain)
    if not ex:
        st.info(t('no_examples'))
        return []
    e1, e2 = st.columns([1, 2])
    with e1:
        case = keep(f'case_{domain}', ex, t('case'))
    with e2:
        img = keep(f'img_{domain}_{case}', ex[case], t('image'), format_func=lambda p: p.name[:48])
    paths = [img]
    ss.sel_whole = (domain == 'msdd' or str(case).startswith('msdd/')) and st.checkbox(t('whole_part'), ss.get('sel_whole', False))
    if ss.sel_whole:
        paths = same_part_images(img)
    st.image([str(p) for p in paths], width=100)
    return paths


def ledger_sidebar(on_open=None):
    """좌측 사이드바: 검사 대장 · 기록 목록 (누르면 본문에 열림) + 엑셀 다운로드."""
    with st.sidebar:
        st.header(t('ledger'))
        rows = records.load(OUT)[::-1]       # 최신순
        n_wait = sum(e['status'] == 'pending' for e in rows)
        flt = keep('flt', ['pending', 'all', 'reject', 'review', 'normal'], t('ledger_filter'),
                   format_func=lambda f: (f'{t("f_pending")} ({n_wait})' if f == 'pending' else
                                          t('f_all') if f == 'all' else verdict_name(f, ss.lang)))
        q = st.text_input(t('ledger_search'), placeholder=t('ledger_search_ph'))
        shown = [e for e in rows
                 if (flt == 'all' or (flt == 'pending' and e['status'] == 'pending') or verdict_key(e) == flt)
                 and (not q or q.lower() in ' '.join(str(e.get(k, '')) for k in ('대상', '품번', '로트', '대표 유형')).lower())]
        if shown:
            st.caption(t('ledger_pick'))
            cur = ss.result['name'] if ss.result else None
            with st.container(height=430):
                for e in shown[:60]:
                    mark = '⏳ ' if e['status'] == 'pending' else ''
                    label = f'{DOT[verdict_key(e)]} {mark}{e["일시"][5:16]} · {e["대상"][:22]}'
                    if st.button(label, key=f'rec_{e["id"]}', width='stretch',
                                 type='primary' if e['id'] == cur else 'secondary',
                                 help=f'{verdict_name(verdict_key(e), ss.lang)} · {STATUS[ss.lang].get(e["status"], "")}'
                                      f' · {t("m_part_no")} {e.get("품번") or "-"} · {t("m_lot")} {e.get("로트") or "-"}'):
                        open_record(e)
                        if on_open:
                            on_open(e)
                        st.rerun()
        else:
            st.caption(t('ledger_empty'))
        st.divider()
        x = OUT / records.XLSX
        if x.exists():
            st.download_button(t('download_xlsx'), x.read_bytes(), file_name=x.name, width='stretch',
                               mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        st.caption(t('records_help'))


def verdict_header(r, compact=False):
    with st.container(key='tour_verdict'):
        _verdict_header(r, compact)


def _verdict_header(r, compact):
    det, sit = r['detection'], r['situation']
    kb_map = {k['type']: k for k in r['knowledge']}
    n_rej = sum(d['level'] == 'reject' for d in det['defects'])
    rep = sit.get('representative')
    badge = (f'<div style="background:{BADGE[det["verdict"]]};color:white;padding:{"6px 12px" if compact else "10px 16px"};'
             f'border-radius:8px;font-size:{18 if compact else 22}px;font-weight:600">'
             f'{t("verdict")}: {verdict_name(det["verdict"], ss.lang)}</div>')
    c1, c2, c3, c4 = st.columns([2, 1, 1, 2])
    c1.markdown(badge, unsafe_allow_html=True)
    c2.metric(t('n_reject'), n_rej)
    c3.metric(t('n_review'), len(det['defects']) - n_rej)
    c4.metric(t('representative'), type_name(rep, kb_map.get(rep), ss.lang) if rep else '-')
    if r['text'].get('summary'):
        st.write(r['text']['summary'])
    route = r.get('routing')
    if route:
        st.caption(t('route_fallback') if route.get('fallback') else
                   t('route_info', domain=t(f'domain_{route["domain"]}'), conf=f'{route["confidence"]:.2f}'))
    if det['verdict'] != 'normal' and r.get('lang') != ss.lang:
        st.caption(t('lang_mismatch', name=LANGS[r['lang']]))


def result_body(r):
    """사진 · 결함 표(수정) · 보고서 문장(편집) · 처리 버튼. 판정을 바꾸는 곳은 여기뿐이다.

    영역마다 key 를 붙여 두어 화면 안내(tour.py)가 강조할 수 있다.
    """
    with st.container(key='tour_photos'):
        _photos_block(r)
    with st.container(key='tour_table'):
        _defects_block(r)
    with st.container(key='tour_text'):
        _text_block(r)
    autosave(r)
    with st.container(key='tour_decision'):
        decision(r)


def _photos_block(r):
    det = r['detection']
    if det.get('views'):
        cols = st.columns(3)
        for i, v in enumerate(det['views']):
            cols[i % 3].image(v['marked_image'], caption=f'{v["view"]} — {verdict_name(v["verdict"], ss.lang)}')
    else:
        a, b = st.columns(2)
        a.image(det['image'], caption=t('original'))
        b.image(det['marked_image'], caption=t('marked'))
    if det.get('tiles', 1) > 1:
        st.caption(t('tiled', n=det['tiles']))


def _defects_block(r):
    det = r['detection']
    kb_map = {k['type']: k for k in r['knowledge']}
    st.subheader(t('defects'))
    if det['defects']:
        names = list(_model(det['domain']).names.values())
        levels = ['reject', 'review', 'exclude']
        df = pd.DataFrame([{
            'No': d['id'], t('col_view'): d.get('view', ''), t('col_type'): d['type'],
            t('col_name'): type_name(d['type'], kb_map.get(d['type']), ss.lang),
            t('col_level'): level_name(d['level'], ss.lang), t('col_conf'): d['conf'],
            t('col_pos'): pos_text(d['position'], ss.lang),
            t('col_size'): f'{d["size_px"][0]}×{d["size_px"][1]}' + (f' ({100 * d["area_ratio"]:.1f}%)' if 'area_ratio' in d else ''),
            t('col_reason'): reason_text(d, ss.lang)}
            for d in sorted(det['defects'], key=lambda d: (d['level'] != 'reject', -d['conf']))])
        if not det.get('views'):
            df = df.drop(columns=[t('col_view')])
        edited = st.data_editor(df, hide_index=True, width='stretch', key=f'ed_{r["name"]}', column_config={
            t('col_type'): st.column_config.SelectboxColumn(options=names, required=True),
            t('col_level'): st.column_config.SelectboxColumn(options=[level_name(x, ss.lang) for x in levels], required=True),
        }, disabled=[c for c in df.columns if c not in (t('col_type'), t('col_level'))])
        b1, b2 = st.columns(2)
        if b1.button(t('apply_edits'), width='stretch'):
            by_id = {d['id']: d for d in det['defects']}
            back = {level_name(x, ss.lang): x for x in levels}
            kept, excluded = [], det.setdefault('excluded', [])
            for _, row in edited.iterrows():
                d = by_id[row['No']]
                lv, ty = back[row[t('col_level')]], row[t('col_type')]
                if lv == 'exclude':
                    excluded.append(d)
                    continue
                if lv != d['level'] or ty != d['type']:
                    d.update(level=lv, type=ty, reason_key='edited', reason=reason_text({'reason_key': 'edited'}))
                kept.append(d)
            det['defects'] = kept
            refresh(r, write=False)
            r.pop('status', None)
            ss.done = None
            persist(r)
            st.rerun()
        if b2.button(t('rewrite'), width='stretch'):
            with st.spinner(t('writing')):
                r['lang'] = ss.lang      # 언어를 바꿨으면 그 언어로 다시 작성
                refresh(r, write=True)
            persist(r)
            st.rerun()
        crops = [d for d in det['defects'] if d.get('crop')][:8]
        if crops:
            with st.expander(t('crops')):
                cols = st.columns(4)
                for i, d in enumerate(crops):
                    cols[i % 4].image(d['crop'], caption=f'#{d["id"]} {d["type"]} {d["conf"]:.2f}')
    else:
        st.success(t('no_defects'))


def _text_block(r):
    det = r['detection']
    kb_map = {k['type']: k for k in r['knowledge']}
    if det['verdict'] != 'normal':
        st.subheader(t('text'))
        tx = r['text']
        tx['summary'] = st.text_area(t('summary'), tx.get('summary', ''), height=70)
        for d in tx.get('defects', []):
            d['description'] = st.text_area(f'{t("feature")} — {type_name(d["type"], kb_map.get(d["type"]), ss.lang)}',
                                            d.get('description', ''), height=70)
        if det['verdict'] == 'reject':
            tx['cause_text'] = st.text_area(t('causes'), tx.get('cause_text', ''), height=90)
            tx['action_immediate'] = st.text_area(t('act_now'), tx.get('action_immediate', ''), height=70)
            tx['action_prevent'] = st.text_area(t('act_prevent'), tx.get('action_prevent', ''), height=70)


PREVIEW_CSS = """<style>
.doc{background:#fff;color:#111;padding:28px 34px;border-radius:6px;font-family:'Malgun Gothic',sans-serif;font-size:13px}
.doc h1{font-size:18px;margin:16px 0 6px;color:#1F3864}.doc h1.title{font-size:26px;color:#111;margin:0 0 6px}
.doc h2{font-size:15px;margin:14px 0 6px;color:#1F3864}
.doc table{border-collapse:collapse;width:100%;margin:6px 0}.doc td,.doc th{border:1px solid #999;padding:4px 6px;vertical-align:top}
.doc td:first-child{min-width:7em;word-break:keep-all}.doc td{word-break:break-word}
.doc img{max-width:100%}.doc p{margin:4px 0}
</style>"""


def report_preview_html(r, cached=False):
    """실제로 저장될 Word 보고서를 임시로 만들어 HTML 로 바꾼다 (보이는 그대로 저장된다).

    cached=True 면 내용이 바뀌지 않았을 때 지난번 HTML 을 그대로 쓴다 (작업창이 2초마다 확인하므로).
    """
    key = (r['name'], _snapshot(r), r.get('lang'), r['part_info'])
    if cached and ss.get('preview_key') == key:
        return ss.preview_html
    import mammoth
    tmp = Path(r['work']) / '_preview.docx'
    if not build_report(r, tmp, r['part_info']):
        return None
    with open(tmp, 'rb') as f:
        html = mammoth.convert_to_html(f, style_map="p[style-name='Title'] => h1.title:fresh").value
    ss.preview_key, ss.preview_html = key, f'{PREVIEW_CSS}<div class="doc">{html}</div>'
    return ss.preview_html


def preview_dialog(r, status, html):
    @st.dialog(t('preview_title'), width='large')
    def _dlg():
        if html:
            st.caption(t('preview_help'))
            with st.container(height=560):
                st.html(html)
        else:
            st.info(t('preview_normal'))
        c1, c2 = st.columns(2)
        if c1.button(t('preview_save'), type='primary', width='stretch'):
            _adopt(finalize(r, status=status))
            st.rerun()
        if c2.button(t('preview_back'), width='stretch'):
            st.rerun()
    _dlg()


def decision(r):
    det = r['detection']
    st.subheader(t('decision'))
    st.caption(t(f'next_{det["verdict"]}'))
    d1, d2 = st.columns(2)
    if d1.button(t(f'confirm_{det["verdict"]}'), type='primary', width='stretch', disabled=bool(ss.done)):
        with st.spinner(t('preview_making')):
            html = report_preview_html(r)
        preview_dialog(r, {'reject': 'sent_wait', 'review': 'review_wait', 'normal': 'normal'}[det['verdict']], html)
    if d2.button(t('false_positive'), width='stretch', disabled=bool(ss.done) or not det['defects']):
        _adopt(reject_false_positive(r))
        st.rerun()
    if ss.done:
        st.success(f'{t("processed")}: {STATUS[ss.lang][ss.done["status"]]}')
        if ss.done.get('record_warning'):
            st.warning(ss.done['record_warning'])
        g1, g2 = st.columns(2)
        if ss.done.get('report') and Path(ss.done['report']).exists():
            p = Path(ss.done['report'])
            st.caption(f'{t("saved_to")}: outputs/{p.relative_to(OUT).as_posix()}')
            g1.download_button(t('download'), p.read_bytes(), file_name=p.name, width='stretch',
                               mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        md = next((OUT / e['md'] for e in records.load(OUT) if e['id'] == r['name'] and e.get('md')), None)
        if md and md.exists():
            g2.download_button(t('download_md'), md.read_bytes(), file_name=md.name, width='stretch')


PANEL_WIDTH = {'normal': 44, 'wide': 60}   # 화면 너비 대비 %


def right_panel_css(open_, width='normal'):
    """오른쪽 작업 패널: 좌측 사이드바처럼 화면 오른쪽에 고정되고 따로 스크롤된다. 열리면 본문은 왼쪽으로 비켜난다."""
    if not open_:
        return
    w = PANEL_WIDTH[width]
    dark = getattr(getattr(st.context, 'theme', None), 'type', 'dark') != 'light'
    bg, line = ('#262730', 'rgba(250,250,250,.15)') if dark else ('#F0F2F6', 'rgba(49,51,63,.15)')
    st.html(f"""<style>
    .st-key-work_panel {{position:fixed; top:3.75rem; right:0; width:{w}vw; height:calc(100vh - 3.75rem);
        overflow-y:auto; overflow-x:hidden; background:{bg}; border-left:1px solid {line};
        padding:0.6rem 1.4rem 2rem; z-index:1000; box-sizing:border-box;}}
    [data-testid="stMainBlockContainer"], .block-container {{padding-right:calc({w}vw + 2rem) !important; max-width:none;}}
    [data-testid="stBottomBlockContainer"] {{padding-right:calc({w}vw + 2rem) !important; max-width:none;}}
    </style>""")


def work_panel(r, on_close=None):
    """오른쪽 작업 패널 내용: [보고서] 미리보기(드래그·복사 가능) / [편집·확정]."""
    with st.container(key='work_panel'):
        h1, h2, h3 = st.columns([5, 1, 1], vertical_alignment='center')
        h1.subheader(f'🛠 {t("work_panel")}')
        wide = ss.get('panel_width', 'normal') == 'wide'
        if h2.button('⇔', key='panel_wide', help=t('panel_wide_help')):
            ss.panel_width = 'normal' if wide else 'wide'
            st.rerun()
        if h3.button('✕', key='panel_close', help=t('panel_close')):
            ss.panel_open = False
            if on_close:
                on_close()
            st.rerun()
        if r is None:
            st.info(t('work_panel_empty'))
            return
        verdict_header(r, compact=True)
        tab_doc, tab_edit = st.tabs([f'📄 {t("tab_report")}', f'🛠 {t("tab_edit")}'])
        with tab_doc:
            html = report_preview_html(r, cached=True)
            if html:
                st.caption(t('copy_help'))
                st.html(html)
            else:
                st.info(t('preview_normal'))
        with tab_edit:
            result_body(r)


def stream_answer(messages, r):
    """Qwen 답변을 스트리밍으로 표시하고 전체 답을 돌려준다."""
    try:
        if r is None or looks_like_history(messages[-1]['content']):     # 이력 질문 → 도구로 검사 이력 조회
            with st.spinner(t('history_thinking')):
                ans = history_answer(messages, ss.lang)
            st.markdown(ans)
            return ans
        return st.write_stream(chat_stream(messages, r, ss.lang))
    except Exception as e:  # noqa: BLE001 — Ollama 미실행 등
        ans = f'{t("chat_error")} ({e})'
        st.error(ans)
        return ans


def quick_questions(compact=False):
    """빠른 질문 버튼 3개 → 누른 질문 문자열 (없으면 None). compact 면 '💡 빠른 질문' 하나로 접는다."""
    q = None
    if compact:
        with st.popover(f'💡 {t("quick_q")}'):
            for key in ('q_why', 'q_cause', 'q_check'):
                if st.button(t(key), width='stretch', key=f'qq_{key}'):
                    q = t(key)
        return q
    cols = st.columns(3)
    for col, key in zip(cols, ('q_why', 'q_cause', 'q_check')):
        if col.button(t(key), width='stretch', key=f'qq_{key}'):
            q = t(key)
    return q


def chat_panel(r, height=520):
    """대시보드형의 오른쪽 대화창 (지금 열린 검사 1건에 대한 질문)."""
    with st.container(key='tour_chat'):
        _chat_panel(r, height)


def _chat_panel(r, height):
    st.subheader(t('chat'))
    st.caption(t('chat_help'))
    box = st.container(height=height)
    for m in ss.chat:
        box.chat_message(m['role']).write(m['content'])
    qq = quick_questions()
    q = st.chat_input(t('chat_ph')) or qq
    if q:
        ss.chat.append({'role': 'user', 'content': q})
        box.chat_message('user').write(q)
        with box.chat_message('assistant'):
            ans = stream_answer(ss.chat, r)
        ss.chat.append({'role': 'assistant', 'content': ans})


__all__ = ['INBOX', 'OUT', 'ROOT', 'IMG_TYPES', 'ss', 'init_state', 't', 'keep', 'save_uploads', 'scan_inbox',
           'start', 'unsure_box', 'open_record', 'run_inbox', 'inbox_summary', 'header', 'meta_inputs', 'domain_input',
           'example_picker', 'ledger_sidebar', 'verdict_header', 'result_body', 'chat_panel', 'stream_answer',
           'quick_questions', 'DOT', 'verdict_name', 'type_name']
