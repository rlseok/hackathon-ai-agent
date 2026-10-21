"""④ 작성한다: 검출 결과 + 지식 → Qwen 이 보고서 문장 작성.

원인 후보·조치 '목록' 은 지식베이스에서 코드가 그대로 가져가고, Qwen 은 주어진 사실로 문장만 쓴다.
"""
import json
import os
from collections import defaultdict

import ollama

from agent.i18n import pos_text, reason_text, type_name
from agent import rag
from agent.knowledge import localize

MODEL = os.environ.get('DEFECT_LLM', 'qwen3:8b')     # fine-tune 모델(qwen3-defect)이 검증되면 DEFECT_LLM=qwen3-defect 로 바꾼다
LANGS = {'ko': '한국어', 'vi': '베트남어(Tiếng Việt)', 'en': '영어(English)'}

SYSTEM = """너는 제조 품질 불량 보고서를 작성하는 보조자다.
규칙:
1. [검출 결과]와 [지식]에 있는 사실만 사용한다. 없는 원인·수치·공정을 만들지 않는다.
2. 원인은 '후보'로 표현하고 단정하지 않는다.
3. 물리적 조치(격리, 수리, 폐기, 측정)는 '작업자 확인 후 실시'로 쓴다.
4. suspected(의심) 검출은 '의심, 재검사 필요'로 표현하고 결함으로 단정하지 않는다.
5. 유형은 영문 type 대신 name 으로 쓴다. 'major', 'opencircuit' 같은 영문 코드를 문장에 넣지 않는다.
6. 사실을 나열만 하고, 주어지지 않은 평가('불일치', '심각함' 등)를 덧붙이지 않는다.
7. 지정된 언어로, 지정된 JSON 형식으로만 답한다."""
NO_KB = '지식베이스 미작성 유형 — 작업자가 기재'
GLOSSARY_VI = ('동박=lá đồng, 배선=đường mạch, 식각=ăn mòn (etching), 노광=phơi sáng, 도금=mạ, 드릴=khoan, '
               '가공면=bề mặt gia công, 세척=rửa, 방청=chống gỉ, 열처리=nhiệt luyện, 주조=đúc, 격리=cách ly')
FINAL_LANG_RULE = {
    'vi': 'QUAN TRỌNG: Viết TẤT CẢ giá trị trong JSON bằng tiếng Việt. Không dùng tiếng Hàn.',
    'en': 'IMPORTANT: Write ALL JSON values in English. Do not use Korean.',
}
WORKER_CHECK = {'ko': ('작업자', '[작업자 확인 후 실시]'),
                'vi': ('công nhân', '[Thực hiện sau khi công nhân xác nhận]'),
                'en': ('worker', '[After worker confirmation]')}


def summarize_detection(detection, knowledge, lang='ko'):
    """LLM 에 넘길 사실을 유형별로 압축 (작은 모델이 긴 목록에서 헷갈리지 않게)."""
    names = {k['type']: type_name(k['type'], k, lang) for k in knowledge}
    by_type = defaultdict(list)
    for d in detection['defects']:
        by_type[d['type']].append(d)
    out = []
    for t, ds in by_type.items():
        long_side = [max(d['size_px']) for d in ds]
        f = {'type': t, 'name': names.get(t, t), 'count': len(ds),
             'max_conf': max(d['conf'] for d in ds),
             'abnormal': sum(d['level'] == 'reject' for d in ds),
             'suspected': sum(d['level'] == 'review' for d in ds),
             'judgment_basis': sorted({reason_text(d, lang) for d in ds})[:3],
             'positions': sorted({(f'{d["view"]} ' if 'view' in d else '') + pos_text(d['position'], lang) for d in ds}),
             'box_long_side_px': f'{min(long_side)}~{max(long_side)}' if len(ds) > 1 else long_side[0]}
        if 'area_ratio' in ds[0]:    # 세그멘테이션: 박스보다 실제 결함 면적이 정확
            f['max_area_of_image'] = f'{100 * max(d["area_ratio"] for d in ds):.2f}%'   # 단위를 붙여 오독 방지
            f['surface_wide'] = sum(d.get('extent') == '전면' for d in ds)
            f['local'] = sum(d.get('extent') == '국부' for d in ds)
        if 'view' in ds[0]:
            f['views'] = sorted({d['view'] for d in ds})
        out.append(f)
    return out


def _kb_facts(knowledge, lang='ko'):
    keys = ('description', 'causes', 'actions', 'measure', 'surface_note')
    knowledge = [localize(k, lang) for k in knowledge]       # 베트남어는 번역된 원인·조치를 LLM 에 준다
    return [{'type': k['type'], 'name': type_name(k['type'], k, lang), 'severity': k.get('severity'),
             **{x: k[x] for x in keys if x in k}} for k in knowledge]


def build_prompt(detection, knowledge, situation, part_info='', lang='ko', refs=None):
    """LLM 에 보낼 (system, user) 프롬프트. fine-tune 데이터(tools/make_sft_data.py)도 이 함수로 만든다."""
    facts = summarize_detection(detection, knowledge, lang)
    extra = [f'{situation[k]["label"]}: {situation[k]["action"]}'
             + (f' (해당 유형: {", ".join(situation[k]["types"])})' if 'types' in situation[k] else '')
             for k in ('part', 'surface_wide', 'multi_type') if k in situation]
    views = (f'부품 {detection.get("part")} 사진 {len(detection["views"])}장 ('
             + ', '.join(f'{v["view"]}={v["verdict"]}' for v in detection['views']) + ')') if detection.get('views') else '사진 1장'
    lang_rule = '' if lang == 'ko' else (' — [지식]이 한국어여도 모든 문장을 이 언어로 번역해 작성한다. 한국어를 섞지 않는다.'
                                         + (f' 용어: {GLOSSARY_VI}' if lang == 'vi' else ''))
    user = f"""[언어] {LANGS[lang]}{lang_rule}
[부품 정보] {part_info or '없음'}
[검사 범위] {views}
[판정] {situation['label']} (대표 유형: {situation.get('representative', '없음')})
[추가 상황] {' / '.join(extra) or '없음'}
[검출 결과] {json.dumps(facts, ensure_ascii=False)}
[지식] {json.dumps(_kb_facts(knowledge, lang), ensure_ascii=False) if knowledge else '없음 (이 도메인은 지식베이스 미작성 — 원인·조치는 작업자가 입력)'}

다음 JSON 으로 답하라:
{{"summary": "판정 요약 1~2문장",
  "defects": [{{"type": "검출 결과의 type 그대로", "description": "위치·개수·크기 포함 특징 1~2문장"}}],
  "cause_text": "대표 유형 중심의 원인 후보 설명 1~3문장 (지식이 없으면 빈 문자열)",
  "action_immediate": "즉시 조치 1~2문장",
  "action_prevent": "점검·재발 방지 1~2문장"}}"""
    if refs:                         # 웹에서 모은 문서(RAG) — [지식]을 보충하는 근거. 쓰면 [S1] 처럼 출처 번호를 붙인다
        user += ('\n\n[참고 자료] (보충 설명용. 사용한 문장 끝에 [S1] 처럼 출처 번호를 붙이고, 자료에 없는 내용은 쓰지 않는다)\n'
                 + rag.context_block(refs))
    if lang != 'ko':                 # 한국어 프롬프트에 끌려 한국어로 쓰는 것을 막기 위해 마지막에 대상 언어로 다시 지시
        user += '\n\n' + FINAL_LANG_RULE[lang]
    return SYSTEM, user, facts


def write_report_text(detection, knowledge, situation, part_info='', lang='ko', model=MODEL):
    try:                             # RAG 가 없어도 보고서는 만든다
        refs = rag.refs_for(knowledge, situation, detection['domain']) if knowledge else []
    except Exception:  # noqa: BLE001 — sentence-transformers 미설치·모델 없음
        refs = []
    system, user, facts = build_prompt(detection, knowledge, situation, part_info, lang, refs)
    res = ollama.chat(model=model, format='json', think=False,
                      messages=[{'role': 'system', 'content': system},
                                {'role': 'user', 'content': user}],
                      options={'temperature': 0.2})
    text = json.loads(res['message']['content'])

    # LLM 이 빠뜨리거나 지어낸 유형은 코드가 바로잡는다
    descs = {d.get('type'): d.get('description', '') for d in text.get('defects', []) if isinstance(d, dict)}
    text['defects'] = [{'type': f['type'], 'description': descs.get(f['type'], '')} for f in facts]
    text['sources'] = [{'id': f'S{i}', 'title': h['title'], 'section': h['section'], 'url': h['source'].split(' ; ')[0],
                        'license': h['license']} for i, h in enumerate(refs, 1)]
    # 원인 후보 목록은 지식베이스 원문 (LLM 생성 아님)
    text['causes'] = [{'type': k['type'], 'cause': c} for k in knowledge for c in k.get('causes', [])]
    for key in ('summary', 'cause_text', 'action_immediate', 'action_prevent'):
        text[key] = str(text.get(key) or '').strip()
    if not knowledge:                # 근거 없는 원인·조치는 쓰지 않는다
        text['cause_text'] = ''
        text['action_immediate'] = text['action_prevent'] = NO_KB
    else:                            # 물리적 조치는 사람이 확정 (규칙 3 보장)
        word, prefix = WORKER_CHECK[lang]
        if word not in text['action_immediate'].lower():
            text['action_immediate'] = f'{prefix} {text["action_immediate"]}'
    return text
