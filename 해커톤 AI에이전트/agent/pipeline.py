"""전체 실행: 사진 → 검출·판정 → 지식 조회 → Qwen 문장 → Word 보고서.

화면(app.py)에서는 analyze → (작업자 수정 → refresh) → finalize / reject_false_positive 순서로 쓴다.

사용:
  python -m agent.pipeline <이미지> [--domain pcb|msdd|mobile] [--part "품번 / 공정"] [--lang ko|vi]
  python -m agent.pipeline <이미지1> <이미지2> ... --domain msdd   # 부품 1개의 여러 방향 사진 → 부품 단위 판정
  python -m agent.pipeline --showcase          # 우수 사례 케이스별 첫 이미지로 일괄 실행
  python -m agent.pipeline --showcase-parts    # 금속 우수 사례를 부품별로 묶어 부품 단위 판정 + 검사자 OK/NG 비교
  python -m agent.pipeline --inbox             # inbox/pcb, inbox/msdd 의 새 사진 일괄 검사 → outputs/inspection_ledger.xlsx
"""
import argparse
import csv
import json
import shutil
import time
from collections import Counter, defaultdict
from pathlib import Path

from agent import records
from agent.detect import ROOT, detect, detect_part, judge, parse_view, short_stem
from agent.i18n import format_meta
from agent.knowledge import lookup, situation
from agent.report import SITUATION_KO, build_report
from agent.writer import write_report_text

OUT = ROOT / 'outputs'
INBOX = ROOT / 'inbox'      # inbox/pcb/, inbox/msdd/, inbox/mobile/ 에 사진을 넣고 일괄 검사
ROUTE = {   # 판정 → (보관 폴더, 결과물 이름, 작업자 확인 없이 처리할 때의 상태)
    'reject': ('abnormal', 'NCR', 'auto_reject'),                       # 부적합 보고서
    'review': ('second_inspection', 'reinspection_hold', 'review_wait'),  # 재검사 의뢰서 (Hold)
    'normal': (None, None, 'normal'),
}
IMG_EXT = {'.jpg', '.jpeg', '.png', '.bmp'}


def save_result(result):
    work = Path(result['work'])
    work.mkdir(parents=True, exist_ok=True)
    p = work / f'{result["name"]}_result.json'
    p.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return p


def load_result(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def register_pending(result, out_root=OUT, xlsx=True, when=None):
    """분석 직후: 결과 저장 + 검사 대장에 '작업자 확인 대기'로 기록. xlsx=False 면 엑셀 대장은 나중에 모아서."""
    save_result(result)
    result['record_warning'] = records.upsert(result, out_root, 'pending', xlsx=xlsx, when=when)
    return result


def analyze(image_paths, domain='pcb', part_info='', lang='ko', out_root=OUT, name=None, tile=None, meta=None):
    """검출·판정·지식 조회·문장 작성까지 (보고서는 아직 만들지 않음 → 작업자 확인 후 finalize).

    image_paths: 사진 1장(경로) 또는 부품 1개의 여러 방향 사진(경로 목록).
    meta: {'part_no': 품번, 'process': 공정 코드(i18n.PROCESS), 'lot': 로트}
    """
    part_info = part_info or format_meta(meta, lang)
    paths = [image_paths] if isinstance(image_paths, (str, Path)) else list(image_paths)
    if len(paths) > 1:
        name = name or f'part_{parse_view(paths[0])[0] or short_stem(paths[0])}'
        work = Path(out_root) / 'work' / name
        det = detect_part(paths, domain, work)
    else:
        name = name or short_stem(paths[0])
        work = Path(out_root) / 'work' / name
        det = detect(paths[0], domain, work, tile=tile)
    result = {'name': name, 'work': str(work), 'part_info': part_info, 'meta': meta or {}, 'lang': lang,
              'detection': det}
    return refresh(result)


def analyze_detected(det, name, part_info='', lang='ko', out_root=OUT, meta=None, source=''):
    """이미 검출·판정까지 끝난 결과(실시간 검사 서버)로 지식 조회·문장 작성만 한다 (YOLO 를 다시 돌리지 않음)."""
    meta = meta or {}
    result = {'name': name, 'work': str(Path(out_root) / 'work' / name), 'part_info': part_info or format_meta(meta, lang),
              'meta': meta, 'lang': lang, 'detection': det, 'source': source}
    return refresh(result)


def refresh(result, write=True):
    """결함 목록(작업자 수정 포함) → 판정·대표 유형·지식 다시 계산. write=True 면 Qwen 문장도 다시 작성."""
    det = result['detection']
    domain = det['domain']
    det['verdict'] = judge(det['defects'], domain)
    kb = lookup((d['type'] for d in det['defects']), domain)
    sit = situation(det, kb)
    result.update(knowledge=kb, situation=sit)
    if det['verdict'] == 'normal':
        result['text'] = {'summary': '기준 신뢰도 이상의 결함이 검출되지 않아 정상으로 판정했습니다.', 'defects': [], 'causes': []}
    elif write or 'text' not in result:
        result['text'] = write_report_text(det, kb, sit, result['part_info'], result['lang'])
    return result


def finalize(result, out_root=OUT, status=None):
    """판정에 따라 보고서 생성(이상/2차검수 폴더) + 검사 대장·md 기록.

    status: 처리 상태 키 (i18n.STATUS). 화면에서 작업자가 확정하면 'sent_wait' 등을 넘긴다.
    """
    out_root = Path(out_root)
    det, name = result['detection'], result['name']
    folder, doc_name, default_status = ROUTE[det['verdict']]
    result['report'] = (build_report(result, out_root / folder / f'{name}_{doc_name}.docx', result['part_info'])
                        if folder else None)
    result['status'] = status or default_status
    save_result(result)
    result['record_warning'] = records.upsert(result, out_root, result['status'])
    return result


def reject_false_positive(result, out_root=OUT):
    """오탐 기각: 정상 처리 + 사진을 재학습용 정상 샘플로 보관."""
    keep = Path(out_root) / 'retraining' / 'normal' / result['detection']['domain']
    keep.mkdir(parents=True, exist_ok=True)
    det = result['detection']
    for v in det.get('views') or [{'image': det['image']}]:
        shutil.copy2(v['image'], keep / Path(v['image']).name)
    det['rejected_defects'] = det['defects']
    det['defects'] = []
    refresh(result, write=False)
    return finalize(result, out_root, status='fp')


def run(image_path, domain='pcb', part_info='', lang='ko', out_root=OUT, tile=None, name=None):
    """사진 1장, 작업자 확인 없이 판정대로 처리. 이상 → outputs/abnormal/, 의심 → outputs/second_inspection/, 모두 inspection_ledger.xlsx."""
    return finalize(analyze(image_path, domain, part_info, lang, out_root, name, tile), out_root)


def run_part(image_paths, domain='msdd', part_info='', lang='ko', out_root=OUT, name=None):
    return finalize(analyze(list(image_paths), domain, part_info, lang, out_root, name), out_root)


def scan_inbox(inbox=INBOX):
    """inbox/<도메인>/ 의 새 사진 목록."""
    return {d: sorted(p for p in (Path(inbox) / d).glob('*') if p.suffix.lower() in IMG_EXT)
            for d in ('pcb', 'msdd', 'mobile') if (Path(inbox) / d).is_dir()}


def process_inbox(lang='ko', meta=None, inbox=INBOX, out_root=OUT, progress=None):
    """대기함 일괄 검사: 사진을 outputs/received/<날짜>/ 로 옮겨 분석한다.

    정상 → 바로 '정상 통과 (일괄 자동)' 처리 / 의심·이상 → '작업자 확인 대기' 로 기록 (화면에서 열어 확인 후 확정).
    금속은 같은 부품의 여러 방향 사진을 묶어 부품 단위로 판정한다.
    progress(i, n, 이름): 진행 표시용 콜백.
    """
    out_root = Path(out_root)
    jobs = []
    for domain, files in scan_inbox(inbox).items():
        dest = out_root / 'received' / time.strftime('%Y%m%d') / domain
        dest.mkdir(parents=True, exist_ok=True)
        moved = []
        for p in files:
            q = dest / p.name
            if q.exists():
                q = dest / f'{p.stem}_{time.strftime("%H%M%S")}{p.suffix}'
            shutil.move(str(p), q)
            moved.append(q)
        groups = defaultdict(list)
        for q in moved:
            pid = parse_view(q)[0] if domain == 'msdd' else None
            groups[pid or q.stem].append(q)
        jobs += [(domain, g) for g in groups.values()]
    done = []
    for i, (domain, group) in enumerate(jobs):
        if progress:
            progress(i, len(jobs), group[0].name)
        r = analyze(group if len(group) > 1 else group[0], domain, lang=lang, out_root=out_root, meta=meta)
        if r['detection']['verdict'] == 'normal':
            finalize(r, out_root, status='normal_auto')
        else:
            register_pending(r, out_root)
        done.append(r)
    if progress:
        progress(len(jobs), len(jobs), '')
    return done


def run_showcase(lang='ko'):
    cases = [('pcb', p) for p in sorted((ROOT / 'results/pcb/showcase').glob('*/originals/images/01_*'))]
    cases += [('msdd', p) for p in sorted((ROOT / 'results/msdd/showcase').glob('*/originals/images/01_*'))]
    cases += [('mobile', p) for p in sorted((ROOT / 'results/mobile/showcase').glob('*/originals/images/01_*'))]
    for domain, img in cases:
        case = img.parents[2].name
        t0 = time.time()
        r = run(img, domain, part_info=f'showcase {domain}/{case}', lang=lang, name=f'{domain}_{case}')
        det = r['detection']
        n_rej = sum(d['level'] == 'reject' for d in det['defects'])
        print(f'[{domain:4s}] {case:16s} 판정={r["situation"]["label"]:3s} 대표={r["situation"].get("representative", "-"):13s} '
              f'이상={n_rej:2d} 의심={len(det["defects"]) - n_rej:2d}  {time.time() - t0:5.1f}s  '
              f'→ {Path(r["report"]).relative_to(OUT) if r["report"] else "이력만 기록"}')


def run_showcase_parts(lang='ko', min_views=2):
    """금속 우수 사례 이미지를 부품별로 묶어 부품 단위 판정. 파일명의 검사자 OK/NG 와 비교."""
    meta = {}
    with open(ROOT / 'results/msdd/meta.csv', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            meta[row['part']] = 'NG' if row['verdict'] == 'NG' or meta.get(row['part']) == 'NG' else 'OK'
    groups = defaultdict(dict)
    for p in sorted((ROOT / 'results/msdd/showcase').glob('*/originals/images/*.jpg')):
        part, view = parse_view(p)
        groups[part].setdefault(view, p)    # 케이스 폴더 간 중복 사진은 한 번만
    tally = defaultdict(int)         # (우리 판정, 검사자) 건수
    for part, views in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        if len(views) < min_views:
            continue
        r = run_part(list(views.values()), 'msdd', part_info=f'부품 {part}', lang=lang)
        inspector = meta.get(part, '?')
        tally[(r['situation']['label'], inspector)] += 1
        by_view = ','.join(f'{v["view"]}:{SITUATION_KO[v["verdict"]]}' for v in r['detection']['views'])
        print(f'[part] {part:18s} 사진 {len(views)}장 판정={r["situation"]["label"]:3s} 검사자={inspector}  방향별={by_view}')
    print('부품 판정 × 검사자:', ', '.join(f'{o}/{i} {n}건' for (o, i), n in sorted(tally.items())))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('images', nargs='*')
    ap.add_argument('--domain', default='pcb', choices=['pcb', 'msdd', 'mobile'])
    ap.add_argument('--part', default='')
    ap.add_argument('--lang', default='ko', choices=['ko', 'vi'])
    ap.add_argument('--tile', choices=['auto', 'on', 'off'], default='auto')
    ap.add_argument('--showcase', action='store_true')
    ap.add_argument('--showcase-parts', action='store_true')
    ap.add_argument('--inbox', action='store_true', help='inbox/pcb, inbox/msdd, inbox/mobile 의 사진을 일괄 검사')
    a = ap.parse_args()
    if a.inbox:
        res = process_inbox(a.lang, progress=lambda i, n, s: print(f'[{i}/{n}] {s}') if s else None)
        print(', '.join(f'{k} {v}' for k, v in Counter(r['detection']['verdict'] for r in res).items()) or '대기함이 비어 있음',
              f'→ {OUT / records.XLSX}')
    elif a.showcase:
        run_showcase(a.lang)
    elif a.showcase_parts:
        run_showcase_parts(a.lang)
    elif len(a.images) > 1:
        r = run_part(a.images, a.domain, a.part, a.lang)
        print(json.dumps(r['text'], ensure_ascii=False, indent=2))
        print('보고서:', r['report'])
    elif a.images:
        r = run(a.images[0], a.domain, a.part, a.lang, tile={'auto': None, 'on': True, 'off': False}[a.tile])
        print(json.dumps(r['text'], ensure_ascii=False, indent=2))
        print('보고서:', r['report'])
    else:
        ap.print_help()
