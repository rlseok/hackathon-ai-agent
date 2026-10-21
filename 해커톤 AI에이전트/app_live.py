"""작업자 확인 화면 — 실시간 검사 (Streamlit).

영상 서버(live/server.py, 포트 8506)가 카메라나 가상 컨베이어 영상을 열고 검사한다. 이 화면은 그 결과를 보기만 한다.
카메라를 열지 않으므로 이 화면, 전용 뷰어(http://localhost:8506/), 다른 PC 의 브라우저를 몇 개 열어도 충돌이 없다.
이상·의심 기판은 영상 서버의 보고 에이전트가 검사 대장에 '작업자 확인 대기'로 올리고, 대시보드(app.py)에서 확정한다.

실행: streamlit run app_live.py --server.port 8505   (영상 서버가 꺼져 있으면 화면의 [영상 서버 시작] 버튼)
"""
import json
import subprocess
import sys
import time
import urllib.request

import streamlit as st

from agent.detect import TAXONOMIES
from agent.i18n import LANGS, T, type_name
from ui import ICONS, OUT, ROOT, app_chrome, init_state, ss

SERVER = 'http://localhost:8506'
DASHBOARD = 'http://localhost:8501'
CHAT = 'http://localhost:8503'      # 오류 기록을 누르면 채팅 화면의 작업 패널로 연다

TXT = {
    'ko': {'title': '실시간 {line} 검사', 'sub': '컨베이어 영상 → 센싱 구역 판정 → AI 보고서 → 대시보드 확인',
           'ng': '이상', 'hold': '의심', 'ok': '정상', 'inspected': '검사', 'alerts': '라인 감시 경고', 'no_alert': '경고 없음',
           'recent': '최근 판정', 'open_chat': '💬 채팅에서 열기', 'pause': '⏸ 일시정지', 'resume': '▶ 재생', 'restart': '⏮ 처음부터', 'reset': '↺ 집계 초기화',
           'viewer': '🖥 전용 뷰어 (프로젝터)', 'dash': '📋 대시보드에서 확인', 'queue': '보고서 대기',
           'off': '영상 서버(포트 8506)가 꺼져 있습니다.', 'start': '영상 서버 시작', 'starting': '영상 서버를 켜는 중… (10~20초)',
           'legend': '얇은 박스 = 실시간 미리보기 · 센싱 구역을 지나면 굵은 박스와 판정 도장(OK / HOLD / NG)',
           'report': {'none': '', 'queued': '보고서 대기', 'writing': 'AI 보고서 작성 중', 'ready': '보고서 초안 → 대시보드 확인 대기',
                      'logged': '대장에 기록 (보고서는 열 때 작성)', 'no_llm': '기록됨 (AI 문장 없음)', 'error': '기록 실패'},
           'streak': '연속 불량 {n}장 — 공정 상태를 점검하세요',
           'type_repeat': '같은 유형 반복: {type} (최근 {of}장 중 {n}장)',
           'location_repeat': '같은 위치 반복: {type} · {position} (최근 {of}장 중 {n}장) — 마스크·드릴 등 공정 점검 권고',
           'ng_rate': '최근 불량률 {pct}% ({n}장)',
           'gt_title': '정답 대조 (영상 정답 json)', 'gt_board': '기판 판정 정확도', 'gt_defect': '결함 검출 F1', 'gt_detail': '결함 기판 {dc}/{db} 잡음 · 정상 기판 {np}/{nb} 통과 · 결함 맞힘 {tp} · 오탐 {fp} · 놓침 {fn}', 'gt_was': '정답'},
    'vi': {'title': 'Kiểm tra {line} thời gian thực', 'sub': 'Video băng chuyền → phán định tại vùng cảm biến → báo cáo AI → xác nhận',
           'ng': 'Bất thường', 'hold': 'Nghi ngờ', 'ok': 'Bình thường', 'inspected': 'Đã kiểm', 'alerts': 'Cảnh báo dây chuyền',
           'no_alert': 'Không có cảnh báo', 'recent': 'Kết quả gần đây', 'open_chat': '💬 Mở trong hội thoại', 'pause': '⏸ Tạm dừng', 'resume': '▶ Tiếp tục',
           'restart': '⏮ Từ đầu', 'reset': '↺ Đặt lại số liệu', 'viewer': '🖥 Màn hình riêng (máy chiếu)',
           'dash': '📋 Xác nhận trên bảng điều khiển', 'queue': 'Chờ báo cáo',
           'off': 'Máy chủ video (cổng 8506) đang tắt.', 'start': 'Khởi động máy chủ video', 'starting': 'Đang khởi động… (10–20 giây)',
           'legend': 'Khung mảnh = xem trước thời gian thực · qua vùng cảm biến thì có khung đậm và dấu kết quả (OK / HOLD / NG)',
           'report': {'none': '', 'queued': 'Chờ báo cáo', 'writing': 'AI đang viết báo cáo', 'ready': 'Bản nháp → chờ xác nhận',
                      'logged': 'Đã ghi sổ (báo cáo viết khi mở)', 'no_llm': 'Đã ghi (không có câu AI)', 'error': 'Ghi thất bại'},
           'streak': '{n} tấm lỗi liên tiếp — hãy kiểm tra công đoạn',
           'type_repeat': 'Lặp lại cùng loại: {type} ({n}/{of} tấm gần nhất)',
           'location_repeat': 'Lặp lại cùng vị trí: {type} · {position} ({n}/{of}) — khuyến nghị kiểm tra công đoạn',
           'ng_rate': 'Tỷ lệ lỗi gần đây {pct}% ({n} tấm)',
           'gt_title': 'Đối chiếu đáp án (json của video)', 'gt_board': 'Độ chính xác theo tấm', 'gt_defect': 'F1 phát hiện lỗi', 'gt_detail': 'Tấm lỗi bắt được {dc}/{db} · tấm tốt cho qua {np}/{nb} · lỗi đúng {tp} · báo nhầm {fp} · bỏ sót {fn}', 'gt_was': 'Đáp án'},
    'en': {'title': 'Live {line} Inspection', 'sub': 'Conveyor video → sensing-zone verdict → AI report → confirm on the dashboard',
           'ng': 'Abnormal', 'hold': 'Suspect', 'ok': 'Normal', 'inspected': 'Inspected', 'alerts': 'Line alerts',
           'no_alert': 'No alerts', 'recent': 'Recent results', 'open_chat': '💬 Open in chat', 'pause': '⏸ Pause', 'resume': '▶ Resume', 'restart': '⏮ Restart',
           'reset': '↺ Reset counts', 'viewer': '🖥 Dedicated viewer (projector)', 'dash': '📋 Confirm on the dashboard',
           'queue': 'Reports queued', 'off': 'The video server (port 8506) is not running.', 'start': 'Start video server',
           'starting': 'Starting the video server… (10–20 s)',
           'legend': 'Thin boxes = live preview · after the sensing zone: bold boxes and a verdict stamp (OK / HOLD / NG)',
           'report': {'none': '', 'queued': 'Report queued', 'writing': 'AI writing report', 'ready': 'Draft ready → confirm on dashboard',
                      'logged': 'Logged (report written when opened)', 'no_llm': 'Logged (no AI text)', 'error': 'Logging failed'},
           'streak': '{n} NG boards in a row — check the process',
           'type_repeat': 'Same type repeating: {type} ({n} of last {of})',
           'location_repeat': 'Same location repeating: {type} · {position} ({n} of last {of}) — check the process',
           'ng_rate': 'Recent NG rate {pct}% ({n} boards)',
           'gt_title': 'Ground-truth check (video json)', 'gt_board': 'Board verdict accuracy', 'gt_defect': 'Defect detection F1', 'gt_detail': 'Defect boards caught {dc}/{db} · normal boards passed {np}/{nb} · defects found {tp} · false alarms {fp} · missed {fn}', 'gt_was': 'Truth'},
}
DOT = {'reject': '🔴', 'review': '🟠', 'normal': '🟢'}
POS = {'vi': {'상단': 'trên', '중앙': 'giữa', '하단': 'dưới', '좌측': 'trái', '우측': 'phải'},
       'en': {'상단': 'top', '중앙': 'center', '하단': 'bottom', '좌측': 'left', '우측': 'right'}}


def L(key):
    return TXT[ss.lang][key]


def tname(t):
    dom = ss.get('live_domain', 'pcb')
    return type_name(t, TAXONOMIES.get(dom, TAXONOMIES['pcb'])['defects'].get(t), ss.lang)


def call(path, timeout=1.5):
    try:
        with urllib.request.urlopen(f'{SERVER}{path}', timeout=timeout) as r:
            return json.loads(r.read().decode('utf-8'))
    except Exception:  # noqa: BLE001 — 서버가 꺼져 있음
        return None


def start_server():
    log = open(OUT / 'live' / 'server.log', 'a', encoding='utf-8') if (OUT / 'live').exists() else subprocess.DEVNULL
    subprocess.Popen([sys.executable, '-m', 'live.server', '--lang', ss.lang], cwd=str(ROOT), stdout=log, stderr=log,
                     creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))


SHOW_EVAL = st.query_params.get('eval') == '1'   # 정답 대조는 확인용 — 주소에 ?eval=1 을 붙였을 때만 보인다
st.set_page_config(page_title='Defect Agent · Live', page_icon=str(ICONS['dash']), layout='wide')
app_chrome('dash')
init_state()

top_l, top_r = st.columns([6, 1], vertical_alignment='center')
_dom = ss['live_domain'] = (call('/state') or {}).get('domain', 'pcb')     # 라인 종류 (영상 서버가 정함)
top_l.title(L('title').format(line=T(f'domain_{_dom}', ss.lang)))
top_l.caption(L('sub'))
with top_r.popover(f'🌐 {LANGS[ss.lang]}', width='content'):
    choice = st.radio('Language', list(LANGS), format_func=LANGS.get, index=list(LANGS).index(ss.lang),
                      label_visibility='collapsed')
    if choice != ss.lang:
        ss.lang = choice
        call(f'/control?lang={choice}')       # 보고서 문장 언어도 같이
        st.rerun()

state = call('/state')
if state is None:
    st.warning(L('off'))
    if st.button(L('start'), type='primary'):
        (OUT / 'live').mkdir(parents=True, exist_ok=True)
        start_server()
        with st.spinner(L('starting')):
            for _ in range(60):
                time.sleep(1)
                if call('/state'):
                    break
        st.rerun()
    st.stop()

left, right = st.columns([3, 1.35], gap='medium')
with left:
    st.html(f'<img src="{SERVER}/stream.mjpg" style="width:100%;border-radius:8px;background:#000;display:block" alt="live">')
    st.caption(L('legend'))
    c1, c2, c3, c4, c5 = st.columns([1, 1, 1.1, 1.6, 1.6])
    if c1.button(L('resume') if state['paused'] else L('pause'), width='stretch'):
        call('/control?cmd=' + ('resume' if state['paused'] else 'pause'))
        st.rerun()
    if c2.button(L('restart'), width='stretch'):
        call('/control?cmd=restart')
    if c3.button(L('reset'), width='stretch'):
        call('/control?cmd=reset')
    c4.link_button(L('viewer'), f'{SERVER}/?lang={ss.lang}', width='stretch')
    c5.link_button(L('dash'), DASHBOARD, width='stretch')


@st.fragment(run_every=1.0)
def panel():
    s = call('/state')
    if s is None:
        st.warning(L('off'))
        return
    n = s['counts']
    m1, m2, m3 = st.columns(3)
    m1.metric(f'🔴 {L("ng")}', n['reject'])
    m2.metric(f'🟠 {L("hold")}', n['review'])
    m3.metric(f'🟢 {L("ok")}', n['normal'])
    st.caption(f'{L("inspected")} {s["inspected"]} · {s["fps"]} fps · {s["infer_ms"]} ms'
               + (f' · {L("queue")} {s["queue"]}' if s['queue'] else ''))
    g = s.get('eval') if SHOW_EVAL else None   # 정답 대조: 시연 화면에는 숨기고 ?eval=1 일 때만 (확인용)
    if g and g['boards']:
        st.markdown(f'**{L("gt_title")}**')
        e1, e2 = st.columns(2)
        e1.metric(L('gt_board'), f'{100 * g["board_acc"]:.1f}%', f'{g["correct"]}/{g["boards"]}', delta_color='off')
        e2.metric(L('gt_defect'), f'{g["f1"]:.3f}', f'P {g["precision"]:.3f} · R {g["recall"]:.3f}', delta_color='off')
        st.caption(L('gt_detail').format(dc=g['defect_caught'], db=g['defect_boards'], np=g['normal_passed'],
                                         nb=g['normal_boards'], tp=g['tp'], fp=g['fp'], fn=g['fn']))
    st.markdown(f'**{L("alerts")}**')
    if s['alerts']:
        for a in s['alerts'][:3]:
            args = {**a, 'type': tname(a['type']) if a.get('type') else '', 'pct': round(100 * a.get('rate', 0)),
                    'position': ' '.join(POS.get(ss.lang, {}).get(w, w) for w in a.get('position', '').split())}
            st.error(f'{a["time"]} · {L(a["kind"]).format(**args)}', icon='⚠️')
    else:
        st.caption(L('no_alert'))
    st.markdown(f'**{L("recent")}**')
    vn = {'reject': L('ng'), 'review': L('hold'), 'normal': L('ok')}
    for e in s['events'][:6]:
        a, b = st.columns([1, 3.2], vertical_alignment='center')
        a.image(f'{SERVER}{e["capture"]}', width=64)
        rep = TXT[ss.lang]['report'].get(e['report'], '')
        gt = e.get('gt') if SHOW_EVAL else None   # 정답 대조 (?eval=1): ✅ 모두 맞음 / ⚠️ 판정은 맞고 결함 일부 다름 / ❌ 판정 틀림
        mark = '' if not gt else (' ✅' if gt['ok'] and not gt['fp'] and not gt['fn'] else ' ⚠️' if gt['ok'] else ' ❌')
        truth = '' if not gt else (f' · {L("gt_was")}: ' + (', '.join(tname(t) for t in gt['gt_types']) or L('ok')))
        b.markdown(f'{DOT[e["verdict"]]} **#{e["seq"]} {vn[e["verdict"]]}**{mark} · {e["time"]}  \n'
                   f'<span style="font-size:0.85em;color:#888">{", ".join(tname(t) for t in e["types"]) or "-"}'
                   f'{truth}{" · " + rep if rep else ""}</span>'
                   + ('' if e['verdict'] == 'normal' else
                      f'  \n<a href="{CHAT}/?open={e["name"]}&lang={ss.lang}" target="_blank">{L("open_chat")}</a>'),
                   unsafe_allow_html=True)


with right:
    panel()
