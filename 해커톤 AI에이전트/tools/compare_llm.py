"""보고서 문장 모델 비교 — 같은 검출 결과로 두 Ollama 모델이 쓴 문장을 나란히 놓고 시간·형식 지표를 잰다.

  python tools/compare_llm.py qwen3:8b qwen3-defect
  → results/llm_compare/compare.md (사람이 읽고 판단할 문장 나란히 + 지표 표), metrics.json

지표 (자동, 품질 판단은 사람이 문장을 읽고):
  - 시간(초), JSON 실패 수
  - 한국어 섞임: 베트남어·영어 보고서인데 한글이 들어간 칸 수
  - 영문 코드 노출: 'missinghole', 'opencircuit' 같은 클래스 코드나 'critical/major/minor' 가 한국어·베트남어 문장에 나온 수
  - 근거 없는 인용: 참고 자료를 주지 않았는데 [S1] 같은 출처 표시를 단 수
"""
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent.detect import detect  # noqa: E402
from agent.pipeline import refresh  # noqa: E402
from agent.writer import write_report_text  # noqa: E402

CASES = [('pcb', '*missinghole'), ('pcb', '*scratch'), ('msdd', '*Porosity'), ('msdd', '*Stain'),
         ('mobile', '*oil'), ('mobile', '*scratch')]
LANGS = ['ko', 'vi', 'en']
FIELDS = ('summary', 'cause_text', 'action_immediate', 'action_prevent')
CODES = re.compile(r'\b(missinghole|opencircuit|shortcircuit|falsecopper|mousebite|pinhole|spur|critical|major|minor)\b', re.I)
HANGUL = re.compile(r'[가-힣]')
WORK = ROOT / 'outputs/_llm_compare'
OUT = ROOT / 'results/llm_compare'


def inputs():
    for domain, pat in CASES:
        folder = {'pcb': 'pcb', 'msdd': 'msdd', 'mobile': 'mobile'}[domain]
        case = next((ROOT / f'results/{folder}/showcase').glob(pat))
        img = sorted((case / 'originals/images').glob('01_*'))[0]
        det = detect(img, domain, WORK / f'{domain}_{case.name}')
        r = {'name': case.name, 'detection': det, 'part_info': '', 'lang': 'ko'}
        refresh(r, write=False)
        yield f'{domain}/{case.name}', r


def score(text, lang):
    vals = [text.get(k, '') for k in FIELDS] + [d.get('description', '') for d in text.get('defects', [])]
    joined = ' '.join(vals)
    return {'hangul_fields': sum(bool(HANGUL.search(v)) for v in vals) if lang != 'ko' else 0,
            'code_leaks': len(CODES.findall(joined)) if lang != 'en' else 0,
            'fake_citations': len(re.findall(r'\[S\d+\]', joined)),
            'chars': len(joined)}


def main(models):
    cases = list(inputs())
    rows, texts = [], {}
    for m in models:
        write_report_text(cases[0][1]['detection'], cases[0][1]['knowledge'], cases[0][1]['situation'], '', 'ko', model=m)  # 모델 올리기 (시간에서 제외)
        for label, r in cases:
            for lang in LANGS:
                t0 = time.time()
                try:
                    text, ok = write_report_text(r['detection'], r['knowledge'], r['situation'], '', lang, model=m), True
                except Exception as e:  # noqa: BLE001
                    text, ok = {'summary': f'(error: {e})'}, False
                sec = time.time() - t0
                rows.append({'model': m, 'case': label, 'verdict': r['detection']['verdict'], 'lang': lang, 'seconds': round(sec, 1),
                             'json_ok': ok, **score(text, lang)})
                texts[(label, lang, m)] = text
                print(f'{m:14s} {label:22s} {lang} {sec:5.1f}s {rows[-1]}')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'metrics.json').write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding='utf-8')

    md = ['# 보고서 문장 모델 비교', '', f'모델: {" vs ".join(models)} · 사례 {len(cases)}개 × 언어 {len(LANGS)}개 (같은 검출 결과, temperature 0.2)', '',
          '| 모델 | 평균 시간(초) | JSON 실패 | 한국어 섞임(칸) | 영문 코드 노출 | 근거 없는 인용 | 평균 길이(자) |', '|---|---|---|---|---|---|---|']
    for m in models:
        rs = [x for x in rows if x['model'] == m]
        md.append(f'| {m} | {sum(x["seconds"] for x in rs) / len(rs):.1f} | {sum(not x["json_ok"] for x in rs)} | '
                  f'{sum(x["hangul_fields"] for x in rs)} | {sum(x["code_leaks"] for x in rs)} | {sum(x["fake_citations"] for x in rs)} | '
                  f'{sum(x["chars"] for x in rs) / len(rs):.0f} |')
    for label, r in cases:
        md += ['', f'## {label} — 판정 {r["detection"]["verdict"]}']
        for lang in LANGS:
            md += ['', f'### {lang}', '', '| 항목 | ' + ' | '.join(models) + ' |', '|---|' + '---|' * len(models)]
            for k in FIELDS:
                md.append(f'| {k} | ' + ' | '.join(texts[(label, lang, m)].get(k, '').replace('|', '/').replace('\n', ' ')
                                                     for m in models) + ' |')
    (OUT / 'compare.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    print('\n'.join(md[:8]))


if __name__ == '__main__':
    main(sys.argv[1:] or ['qwen3:8b', 'qwen3-defect'])
