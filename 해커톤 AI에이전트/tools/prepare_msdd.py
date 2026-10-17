"""MSDD Roboflow export(msdd_raw)를 학습용 데이터셋으로 정리한다.

- 'Normal' 클래스(부품 전체 윤곽 폴리곤)를 제거하고 클래스 번호를 당긴다
  -> Normal 만 있던 이미지는 빈 라벨(정상/배경 이미지)이 된다
- 부품 단위(예: 00007_S57345-32-)로 묶어 train/val/test 재분할 (같은 부품의 다른 촬영이 split 을 넘지 않게)
- 폴리곤 라벨은 그대로 유지 (세그멘테이션 학습용). 검출 모델로 학습해도 ultralytics 가 bbox 로 변환한다
- 파일명의 OK/NG(검사자 판정)는 meta.csv 에 기록 (라벨과 별개 정보)

사용: python prepare_msdd.py <msdd_raw> <출력 폴더> [--seed 0]
"""
import argparse
import collections
import random
import re
import shutil
from pathlib import Path

import yaml

SRC_SPLITS = ['train', 'valid', 'test']
SPLITS = {'train': 0.8, 'val': 0.1, 'test': 0.1}
DROP = 'Normal'
NAME_RE = re.compile(r'^(\d+_[^_]+?)_(CAM\d+)_(.*)_(OK|NG)$')


def clean_stem(stem):
    stem = re.sub(r'\.rf\.[0-9a-f]+$', '', stem)
    return re.sub(r'_(jpg|jpeg|png|bmp)$', '', stem, flags=re.I)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src', type=Path)
    ap.add_argument('dst', type=Path)
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--trials', type=int, default=5000)
    args = ap.parse_args()

    src_names = yaml.safe_load((args.src / 'data.yaml').read_text(encoding='utf-8'))['names']
    names = [n for n in src_names if n != DROP]
    remap = {i: names.index(n) for i, n in enumerate(src_names) if n != DROP}

    # 1) 이미지 수집 + 라벨 변환
    items = []  # (part, img, lines, meta)
    for sp in SRC_SPLITS:
        for img in sorted((args.src / sp / 'images').iterdir()):
            st = clean_stem(img.stem)
            m = NAME_RE.match(st)
            part, cap, verdict = (m.group(1), m.group(3), m.group(4)) if m else (st, '', '')
            lines = []
            for line in (args.src / sp / 'labels' / (img.stem + '.txt')).read_text().splitlines():
                p = line.split()
                if p and int(p[0]) in remap:
                    lines.append(' '.join([str(remap[int(p[0])])] + p[1:]))
            items.append((part, img, lines, (cap, verdict)))

    groups = collections.defaultdict(list)
    for it in items:
        groups[it[0]].append(it)
    gcount = {g: collections.Counter(int(l.split()[0]) for it in v for l in it[2])
              for g, v in groups.items()}

    # 2) 부품 단위 배정: 부품 수를 비율대로 나누는 무작위 배정을 여러 번 시도해
    #    클래스 비율 오차가 가장 작은 것을 고른다 (부품당 이미지 수가 거의 같아 이미지 비율도 맞춰진다)
    rng = random.Random(args.seed)
    parts = sorted(groups)
    total = collections.Counter()
    for c in gcount.values():
        total.update(c)
    n_total = len(items)
    cuts = [round(len(parts) * SPLITS['train']),
            round(len(parts) * (SPLITS['train'] + SPLITS['val']))]

    def evaluate(order):
        assign = {g: 'train' if i < cuts[0] else 'val' if i < cuts[1] else 'test'
                  for i, g in enumerate(order)}
        cur = {s: collections.Counter() for s in SPLITS}
        for g, s in assign.items():
            cur[s].update(gcount[g])
        err = sum(abs(cur[s][c] / total[c] - r) for s, r in SPLITS.items() for c in total)
        return err, assign, cur

    best = None
    for _ in range(args.trials):
        order = parts[:]
        rng.shuffle(order)
        res = evaluate(order)
        if best is None or res[0] < best[0]:
            best = res
    _, assign, cur = best
    cur_n = collections.Counter(assign[it[0]] for it in items)

    # 3) 저장
    if args.dst.exists():
        raise SystemExit(f'{args.dst} 가 이미 있습니다. 지우거나 다른 경로를 지정하세요.')
    for s in SPLITS:
        (args.dst / 'images' / s).mkdir(parents=True)
        (args.dst / 'labels' / s).mkdir(parents=True)
    empty = collections.Counter()
    meta = ['image,split,part,capture,verdict,n_defects']
    for part, img, lines, (cap, verdict) in items:
        s = assign[part]
        shutil.copy2(img, args.dst / 'images' / s / img.name)
        (args.dst / 'labels' / s / (img.stem + '.txt')).write_text(
            '\n'.join(lines) + ('\n' if lines else ''))
        if not lines:
            empty[s] += 1
        meta.append(f'{img.name},{s},{part},{cap},{verdict},{len(lines)}')
    (args.dst / 'meta.csv').write_text('\n'.join(meta) + '\n', encoding='utf-8')
    (args.dst / 'data.yaml').write_text(
        f'path: {args.dst.resolve().as_posix()}\n'
        'train: images/train\nval: images/val\ntest: images/test\n\n'
        f'nc: {len(names)}\nnames: {names}\n', encoding='utf-8')

    # 4) 리포트
    print(f'removed class: {DROP}, remap: {{{", ".join(f"{src_names[k]}:{k}->{v}" for k, v in remap.items())}}}')
    print(f'parts {len(groups)}, images {n_total}')
    print(f'{"class":10s}' + ''.join(f'{s:>14s}' for s in SPLITS))
    for i, n in enumerate(names):
        print(f'{n:10s}' + ''.join(f'{cur[s][i]:7d} ({cur[s][i] / total[i]:4.0%})' for s in SPLITS))
    print(f'{"images":10s}' + ''.join(f'{cur_n[s]:7d} ({cur_n[s] / n_total:4.0%})' for s in SPLITS))
    print(f'{"empty":10s}' + ''.join(f'{empty[s]:14d}' for s in SPLITS))
    print(f'{"parts":10s}' + ''.join(f'{sum(1 for v in assign.values() if v == s):14d}' for s in SPLITS))


if __name__ == '__main__':
    main()
