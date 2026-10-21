"""② 찾는다: 결함 유형 → 한글명·심각도·원인 후보·조치 (taxonomy YAML 조회)."""
from pathlib import Path

import yaml

from agent.detect import TAXONOMIES

# 베트남어 번역 (원인·조치·설명). 있으면 베트남어 보고서·프롬프트에 한국어 원문 대신 쓴다 (knowledge/translations_vi.yaml)
_KDIR = Path(__file__).resolve().parents[1] / 'knowledge'
TRANSLATIONS = {l: (yaml.safe_load((_KDIR / f'translations_{l}.yaml').read_text(encoding='utf-8'))
                    if (_KDIR / f'translations_{l}.yaml').exists() else {}) for l in ('vi', 'en')}

SEVERITY_ORDER = {'critical': 0, 'major': 1, 'minor': 2}


def kb_for(domain):
    return TAXONOMIES[domain]['defects']


def lookup(defect_types, domain='pcb'):
    """검출된 유형들 → 지식 항목 (심각도 높은 순)."""
    kb = kb_for(domain)
    items = []
    for t in sorted(set(defect_types)):
        info = kb.get(t)
        if info:
            item = {'type': t, **info}
            for l in ('vi', 'en'):
                tr = TRANSLATIONS[l].get(domain, {}).get(t)
                if tr:
                    item[l] = tr
            items.append(item)
    return sorted(items, key=lambda x: SEVERITY_ORDER.get(x['severity'], 9))


def situation(detection, knowledge):
    """판정 + 지식 → 에이전트 동작 안내 (taxonomy 의 situations).

    대표 유형: '이상' 으로 판정된 유형 중 심각도 최고. 없으면 전체 중 심각도 최고.
    심각도가 같으면 최고 신뢰도 → 검출 수 순으로 정한다.
    """
    sits = TAXONOMIES[detection['domain']]['situations']
    verdict = detection['verdict']
    s = dict(sits[verdict])
    defects = detection['defects']
    types = {d['type'] for d in defects}
    if len(types) > 1:
        s['multi_type'] = sits['multi_type']
    surface = sorted({d['type'] for d in defects if d.get('extent') == '전면'})
    if surface and 'surface_wide' in sits:
        s['surface_wide'] = {**sits['surface_wide'], 'types': surface}
    if detection.get('views') and 'part' in sits:
        s['part'] = sits['part']
    strong = {d['type'] for d in defects if d['level'] == 'reject'}
    pool = [k for k in knowledge if k['type'] in strong] or knowledge

    def rank(k):
        ds = [d for d in defects if d['type'] == k['type']]
        return (SEVERITY_ORDER.get(k['severity'], 9), -max(d['conf'] for d in ds), -len(ds))

    if pool:
        s['representative'] = min(pool, key=rank)['type']
    elif defects:                    # 지식베이스에 없는 유형뿐: 신뢰도 최고 유형
        s['representative'] = defects[0]['type']
    return s


def localize(k, lang='ko'):
    """지식 항목을 해당 언어 본문(설명·원인·조치)으로 바꾼 사본. 번역이 없으면 원문(한국어) 그대로."""
    tr = k.get(lang) if isinstance(k.get(lang), dict) else None
    if lang == 'ko' or not tr:
        return k
    return {**k, **{x: tr[x] for x in ('description', 'causes', 'actions') if x in tr}}
