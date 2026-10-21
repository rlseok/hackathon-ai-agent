"""통합 점검 (LLM 없이): 새 기능이 기존 pipeline 과 충돌 없이 이어지는지 확인한다.

Qwen 호출은 가짜 문장으로 바꿔 Ollama 없이 돈다. 검사 대장·보고서·알림은 임시 폴더에만 쓴다.
확인 항목: ① 도메인 직접 지정(기존 방식)과 'auto' ② 보고서 3개 언어 ③ 검사 대장·알림 ④ inbox 일괄 검사(자동 분류 포함)
          ⑤ 이력 조회 도구 ⑥ RAG 검색
사용: python tools/smoke_test.py      (패키지 폴더에서)
"""
import glob
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent import history, pipeline, rag, records, router  # noqa: E402


def fake_text(det, kb, sit, part_info='', lang='ko', **_):
    return {'summary': f'[smoke {lang}] {det["verdict"]}',
            'defects': [{'type': d['type'], 'description': 'smoke'} for d in {x['type']: x for x in det['defects']}.values()],
            'causes': [{'type': k['type'], 'cause': c} for k in kb for c in k.get('causes', [])],
            'cause_text': 'smoke [S1]', 'action_immediate': '[smoke]', 'action_prevent': 'smoke',
            'sources': [{'id': 'S1', 'title': 't', 'section': 's', 'url': 'u', 'license': 'l'}]}


pipeline.write_report_text = fake_text           # Ollama 대신
results, fails = [], []


def check(name, ok, info=''):
    results.append((name, ok, info))
    if not ok:
        fails.append(name)
    print(f'[{"OK" if ok else "FAIL"}] {name} {info}')


def pick_images():
    out = {'pcb': sorted(glob.glob(str(ROOT / 'results/pcb/showcase/*/originals/images/01_*')))[:1],
           'msdd': sorted(glob.glob(str(ROOT / 'results/msdd/showcase/*/originals/images/01_*')))[:1]}
    d = ROOT.parent / 'data'
    out['mobile'] = sorted(glob.glob(str(d / 'mobile_surface/images/test/*.jpg')))[:1]     # 학습 데이터 폴더가 없으면 건너뜀
    return {k: v[0] for k, v in out.items() if v}


def main():
    tmp = Path(tempfile.mkdtemp(prefix='smoke_'))
    imgs = pick_images()
    check('예시 사진 찾음', len(imgs) >= 2, str(list(imgs)))
    use_router = router.available()
    check('라우터 파일 있음', use_router, '(없으면 pcb 로 처리하는 대체 동작)')

    for dom, img in imgs.items():
        # ① 기존 방식: 도메인 직접 지정, 위치 인자 그대로
        r = pipeline.analyze(img, dom, lang='vi', out_root=tmp, name=f'{dom}_explicit')
        check(f'{dom}: 직접 지정 analyze', r['detection']['domain'] == dom and r['routing'] is None, r['detection']['verdict'])
        pipeline.finalize(r, tmp)
        ok_doc = r['detection']['verdict'] == 'normal' or (r['report'] and Path(r['report']).exists())
        check(f'{dom}: finalize → 보고서/기록', ok_doc)
        # ② auto
        if use_router:
            a = pipeline.analyze(img, 'auto', out_root=tmp, name=f'{dom}_auto')
            check(f'{dom}: auto 라우팅', a['detection']['domain'] == dom, f'→ {a["routing"]["domain"]} {a["routing"]["confidence"]}')
    # ③ 보고서 3개 언어 (대표 1건)
    dom, img = next(iter(imgs.items()))
    for lang in ('ko', 'vi', 'en'):
        r = pipeline.analyze(img, dom, lang=lang, out_root=tmp, name=f'{dom}_{lang}')
        pipeline.finalize(r, tmp)
        check(f'보고서 {lang}', r['detection']['verdict'] == 'normal' or Path(r['report']).stat().st_size > 5000)
    check('검사 대장 엑셀', (tmp / records.XLSX).exists())
    check('알림 기록', (tmp / 'notifications.jsonl').exists() or all(
        x['detection']['verdict'] == 'normal' for x in [r]), '(이상·의심이 하나라도 있으면 생김)')

    # ④ inbox: 폴더 지정 + 바로 아래 사진(자동 분류)
    inbox = tmp / 'inbox'
    for dom, img in imgs.items():
        if dom == 'pcb':
            (inbox / 'pcb').mkdir(parents=True, exist_ok=True)
            shutil.copy(img, inbox / 'pcb' / f'a_{Path(img).name}')
        elif use_router:
            shutil.copy(img, inbox / f'b_{Path(img).name}')
    n_loose = len([p for p in inbox.glob('*') if p.is_file()])
    res = pipeline.process_inbox('ko', inbox=inbox, out_root=tmp / 'inb')
    check('inbox 일괄 검사', len(res) >= 1 + (n_loose if use_router else 0) - len(list((inbox / '_unsure').glob('*'))),
          f'{len(res)}건, 자동분류 대상 {n_loose}장, 미확정 {len(list((inbox / "_unsure").glob("*")))}장')
    # ⑤ 이력 조회 도구
    t = history.make_tools(tmp)
    cnt = json.loads(t['count_inspections']())
    check('이력 조회 도구', cnt['total'] >= 1, str(cnt['by_verdict']))
    # ⑥ RAG
    try:
        hits = rag.search('단선 원인', 'pcb', k=2)
        check('RAG 검색', len(hits) >= 1, hits[0]['section'] if hits else '')
    except Exception as e:  # noqa: BLE001
        check('RAG 검색', False, str(e)[:80])

    shutil.rmtree(tmp, ignore_errors=True)
    print(f'\n{len(results) - len(fails)}/{len(results)} 통과' + (f' — 실패: {fails}' if fails else ''))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
