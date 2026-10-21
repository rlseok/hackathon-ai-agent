"""대화 2단계: 검사 이력 조회 (Qwen tool calling).

"오늘 의심 몇 건?", "이 로트에서 반복되는 결함은?", "예전에 비슷한 단선 사례는?" 같은 질문을
records.jsonl 을 읽는 도구로 답한다. 도구는 읽기 전용이라 판정·기록을 바꾸지 못한다.
"""
import json
import time
from collections import Counter

import ollama

from agent import records
from agent.writer import LANGS, MODEL

HISTORY_WORDS = ('오늘', '어제', '이번 주', '이번주', '이번 달', '몇 건', '몇건', '이력', '기록', '과거', '예전', '지난', '비슷한', '유사',
                 '대기', '로트', '품번', '반복', '통계', '합계',
                 'hôm nay', 'hôm qua', 'tuần này', 'bao nhiêu', 'lịch sử', 'trước đây', 'tương tự', 'chờ', 'lô', 'thống kê',
                 'today', 'yesterday', 'this week', 'how many', 'history', 'past', 'similar', 'pending', 'lot', 'statistics')
VERDICT_KEYS = {'normal', 'review', 'reject'}

SYSTEM = """너는 제조 품질 검사 이력을 조회해 답하는 에이전트다. 반드시 도구를 호출해 얻은 결과만 근거로 답한다.
규칙:
1. 숫자·날짜·ID 는 도구 결과 그대로 쓴다. 도구 결과에 없으면 "이력에 없습니다"라고 답한다.
2. 판정(normal 정상 / review 의심 / reject 이상)을 바꾸거나 기록을 고칠 수는 없다. 그런 요청은 화면에서 하도록 안내한다.
3. 오늘 날짜는 {today} 이다. '오늘/어제/이번 주' 는 이 날짜로 계산해 도구의 date_from, date_to(YYYY-MM-DD)에 넣는다.
4. 질문한 언어로 3~6문장 이내로 답한다 (기본 언어: {lang}). 사례를 말할 때는 ID 를 함께 적는다."""


def looks_like_history(text):
    low = text.lower()
    return any(w in low for w in HISTORY_WORDS)


def _filter(entries, date_from='', date_to='', verdict='', domain='', part_no='', lot='', defect_type='', status=''):
    out = []
    for e in entries:
        day = e['일시'][:10]
        if date_from and day < date_from or date_to and day > date_to:
            continue
        if verdict and e['verdict'] != verdict or domain and e['domain'] != domain:
            continue
        if part_no and part_no.lower() not in str(e.get('품번', '')).lower():
            continue
        if lot and lot.lower() not in str(e.get('로트', '')).lower():
            continue
        if status and e['status'] != status:
            continue
        if defect_type and not any(d['클래스'] == defect_type for d in e['defects']):
            continue
        out.append(e)
    return out


def _brief(e):
    return {'id': e['id'], 'date': e['일시'], 'domain': e['domain'], 'verdict': e['verdict'], 'status': e['status'],
            'representative_type': e['rep'], 'part_no': e.get('품번') or None, 'lot': e.get('로트') or None,
            'process': e.get('process') or None, 'reject_count': e['이상'], 'review_count': e['의심'],
            'report': e.get('보고서') or None}


def make_tools(out_root):
    """도구 함수 (docstring 이 Qwen 에게 보이는 설명이 된다)."""
    def count_inspections(date_from: str = '', date_to: str = '', verdict: str = '', domain: str = '',
                          part_no: str = '', lot: str = '', defect_type: str = '', status: str = '') -> str:
        """Count inspections and group them by verdict. Filters are all optional.

        Args:
            date_from: start date YYYY-MM-DD (inclusive)
            date_to: end date YYYY-MM-DD (inclusive)
            verdict: one of normal, review, reject
            domain: one of pcb, msdd, mobile
            part_no: part number (substring match)
            lot: lot number (substring match)
            defect_type: defect class name, e.g. short, Scratch, oil
            status: processing status key, e.g. pending, sent_wait, normal_auto, fp
        """
        es = _filter(records.load(out_root), date_from, date_to, verdict, domain, part_no, lot, defect_type, status)
        return json.dumps({'total': len(es), 'by_verdict': dict(Counter(e['verdict'] for e in es)),
                           'by_domain': dict(Counter(e['domain'] for e in es)),
                           'by_representative_type': dict(Counter(e['rep'] for e in es if e['rep']))}, ensure_ascii=False)

    def list_inspections(date_from: str = '', date_to: str = '', verdict: str = '', domain: str = '',
                         part_no: str = '', lot: str = '', defect_type: str = '', status: str = '', limit: int = 10) -> str:
        """List the most recent inspections matching the filters (newest first).

        Args:
            date_from: start date YYYY-MM-DD (inclusive)
            date_to: end date YYYY-MM-DD (inclusive)
            verdict: one of normal, review, reject
            domain: one of pcb, msdd, mobile
            part_no: part number (substring match)
            lot: lot number (substring match)
            defect_type: defect class name
            status: processing status key, e.g. pending
            limit: maximum number of rows (default 10)
        """
        es = _filter(records.load(out_root), date_from, date_to, verdict, domain, part_no, lot, defect_type, status)
        es = sorted(es, key=lambda e: e['일시'], reverse=True)[:max(1, min(int(limit), 30))]
        return json.dumps([_brief(e) for e in es], ensure_ascii=False)

    def similar_cases(defect_type: str, domain: str = '', limit: int = 5) -> str:
        """Find past inspections that contained the same defect class, with what was decided.

        Args:
            defect_type: defect class name, e.g. short, Porosity, oil
            domain: optional domain filter (pcb, msdd, mobile)
            limit: maximum number of cases (default 5)
        """
        es = _filter(records.load(out_root), domain=domain, defect_type=defect_type)
        es = sorted(es, key=lambda e: e['일시'], reverse=True)[:max(1, min(int(limit), 15))]
        rows = []
        for e in es:
            ds = [d for d in e['defects'] if d['클래스'] == defect_type]
            rows.append({**_brief(e), 'matching_defects': [{'conf': d['신뢰도'], 'level': d['level'], 'position': d['위치']}
                                                           for d in ds][:3]})
        return json.dumps(rows, ensure_ascii=False)

    return {f.__name__: f for f in (count_inspections, list_inspections, similar_cases)}


def answer(messages, lang='ko', out_root=None, model=MODEL, max_rounds=4):
    """이력 질문에 도구로 답한다. messages: [{'role','content'}...] → 답변 문자열."""
    from agent.pipeline import OUT
    tools = make_tools(out_root or OUT)
    system = SYSTEM.format(today=time.strftime('%Y-%m-%d'), lang=LANGS[lang])
    msgs = [{'role': 'system', 'content': system}, *messages[-8:]]
    for _ in range(max_rounds):
        res = ollama.chat(model=model, messages=msgs, tools=list(tools.values()), think=False,
                          options={'temperature': 0.1})
        msg = res['message']
        if not msg.get('tool_calls'):
            return (msg.get('content') or '').strip()
        msgs.append(msg)
        for call in msg['tool_calls']:
            fn = tools.get(call['function']['name'])
            try:
                out = fn(**call['function']['arguments']) if fn else '{"error": "unknown tool"}'
            except Exception as e:  # noqa: BLE001 — 잘못된 인자 등은 모델이 고치도록 알려준다
                out = json.dumps({'error': str(e)})
            msgs.append({'role': 'tool', 'tool_name': call['function']['name'], 'content': out})
    return ollama.chat(model=model, messages=msgs, think=False, options={'temperature': 0.1})['message']['content'].strip()
