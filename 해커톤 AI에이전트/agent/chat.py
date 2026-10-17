"""에이전트 대화 (1단계: 검사 결과 기반 Q&A).

지금 화면의 검사 결과·지식베이스를 프롬프트에 넣고 Qwen 이 답한다. 판정은 바꾸지 못한다 (작업자가 화면에서 수정).
"""
import json

import ollama

from agent.i18n import situation_text, type_name
from agent.writer import LANGS, MODEL, _kb_facts, summarize_detection

SYSTEM = """너는 제조 현장 작업자를 돕는 품질 검사 에이전트다. 아래 [검사 결과]와 [지식]만 근거로 답한다.
규칙:
1. 근거에 없는 내용은 "검사 결과나 지식베이스에 없는 정보"라고 말하고 추측하지 않는다.
2. 판정(정상/의심/이상)은 네가 바꿀 수 없다. 판정을 바꾸자는 요청에는 이렇게 답한다:
   "판정은 제가 바꿀 수 없습니다. 실물을 확인한 뒤 결함 표의 '판정' 칸을 바꾸고 [수정 반영]을 누르거나, 오탐이면 [오탐 기각]을 눌러 주세요."
   (질문 언어가 다르면 같은 뜻으로 번역해서 답한다)
3. 격리·수리·폐기 같은 물리적 조치는 작업자 확인 후 실시하도록 안내한다.
4. 원인은 '후보'로 말하고 단정하지 않는다.
5. 3~6문장 이내로 짧고 명확하게, 질문한 언어로 답한다 (기본 언어: {lang}).
6. 결함 유형은 영문 코드 대신 name 으로 부른다."""


def build_context(result, lang='ko'):
    det, kb, sit = result['detection'], result['knowledge'], result['situation']
    top = situation_text(sit, det['verdict'], lang)
    extra = {k: situation_text(sit[k], k, lang)['action'] for k in ('part', 'surface_wide', 'multi_type') if k in sit}
    rep = sit.get('representative')
    ctx = {
        'verdict': top['label'],
        'next_step': top.get('action'),
        'representative': type_name(rep, next((k for k in kb if k['type'] == rep), None), lang) if rep else None,
        'situations': extra,
        'part_info': result.get('part_info') or None,
        'photos': [f'{v["view"]}={v["verdict"]}' for v in det['views']] if det.get('views') else 1,
        'defects': summarize_detection(det, kb, lang),
        'excluded_by_worker': len(det.get('excluded', [])),
        'report_text': {k: result['text'].get(k) for k in ('summary', 'cause_text', 'action_immediate', 'action_prevent')
                        if result['text'].get(k)},
    }
    return (f'[검사 결과]\n{json.dumps(ctx, ensure_ascii=False)}\n'
            f'[지식]\n{json.dumps(_kb_facts(kb, lang), ensure_ascii=False) if kb else "없음"}')


EDIT_FIELDS = ('summary', 'cause_text', 'action_immediate', 'action_prevent')
EDIT_WORDS = ('고쳐', '바꿔', '수정', '다시 써', '고치', '줄여', '늘려', '추가해', '빼', '삭제', '지워', '대신',
              'sửa', 'đổi', 'viết lại', 'xóa', 'thêm', 'rút gọn',
              'change', 'rewrite', 'edit', 'replace', 'shorten', 'remove', 'delete', 'add ')

EDIT_SYSTEM = """너는 제조 품질 보고서 문장을 고치는 보조자다. 작업자의 요청대로 [현재 문장]의 해당 부분만 고친다.
규칙:
1. 요청한 부분만 바꾸고 나머지 필드는 그대로 둔다. 바뀐 필드만 changes 에 넣는다.
2. 판정(정상/의심/이상), 결함 유형·개수·신뢰도 같은 검사 사실은 바꾸지 않는다. 그런 요청이면 changes 를 비우고 note 에
   "판정과 결함 정보는 작업창의 결함 표에서 수정하세요" 라고 쓴다.
3. [검사 결과]와 [지식]에 없는 원인·수치를 만들지 않는다.
4. 원래 문장의 언어({lang})로 쓴다.
5. JSON 으로만 답한다: {{"changes": {{"summary"|"cause_text"|"action_immediate"|"action_prevent": "새 문장",
   "defects": [{{"type": "클래스", "description": "새 문장"}}]}}, "note": "무엇을 바꿨는지 한 문장 (질문 언어로)"}}"""


def looks_like_edit(text):
    """'이 부분 고쳐줘' 같은 수정 요청인지 (간단한 낱말 기준)."""
    low = text.lower()
    return any(w in low for w in EDIT_WORDS)


def propose_edit(request, result, lang='ko', model=MODEL):
    """작업자의 수정 요청(보고서에서 복사한 문장 포함 가능) → 바꿀 필드 제안. 실제 반영은 작업자가 [적용]을 눌렀을 때."""
    tx = result['text']
    current = {k: tx.get(k, '') for k in EDIT_FIELDS if tx.get(k)}
    current['defects'] = [{'type': d['type'], 'description': d.get('description', '')} for d in tx.get('defects', [])]
    user = (f'[현재 문장]\n{json.dumps(current, ensure_ascii=False)}\n\n{build_context(result, lang)}\n\n'
            f'[작업자 요청]\n{request}')
    res = ollama.chat(model=model, format='json', think=False, options={'temperature': 0.2},
                      messages=[{'role': 'system', 'content': EDIT_SYSTEM.format(lang=LANGS[result.get('lang', lang)])},
                                {'role': 'user', 'content': user}])
    out = json.loads(res['message']['content'])
    raw = out.get('changes') or {}
    changes = {k: str(v).strip() for k, v in raw.items() if k in EDIT_FIELDS and str(v).strip() and str(v).strip() != tx.get(k)}
    known = {d['type']: d.get('description', '') for d in tx.get('defects', [])}
    defs = [d for d in raw.get('defects', []) if isinstance(d, dict) and d.get('type') in known
            and d.get('description') and d['description'] != known[d['type']]]
    if defs:
        changes['defects'] = [{'type': d['type'], 'description': str(d['description']).strip()} for d in defs]
    return {'changes': changes, 'note': str(out.get('note', '')).strip()}


def apply_edit(result, changes):
    """제안을 결과에 반영 (호출한 쪽에서 저장)."""
    tx = result['text']
    for k, v in changes.items():
        if k == 'defects':
            by_type = {d['type']: d for d in tx.get('defects', [])}
            for d in v:
                if d['type'] in by_type:
                    by_type[d['type']]['description'] = d['description']
        elif k in EDIT_FIELDS:
            tx[k] = v
    return result


def chat_stream(messages, result, lang='ko', model=MODEL, history=10):
    """messages: [{'role': 'user'|'assistant', 'content': ...}] → 답변 조각을 차례로 돌려준다."""
    system = SYSTEM.format(lang=LANGS[lang]) + '\n\n' + build_context(result, lang)
    stream = ollama.chat(model=model, think=False, stream=True, options={'temperature': 0.3},
                         messages=[{'role': 'system', 'content': system}, *messages[-history:]])
    for chunk in stream:
        yield chunk['message']['content']
