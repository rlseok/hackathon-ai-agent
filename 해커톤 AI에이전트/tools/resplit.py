"""PCB_dataset을 원본 이미지 단위로 재분할해 pcb_agent/data/pcb_v2 를 만든다.

- 같은 원본(예: 08_short_05)에서 잘린 조각은 모두 같은 split 으로 보낸다 (누수 방지)
- split 간 클래스 비율이 비슷하도록 그룹을 탐욕적으로 배정한다
- 폴리곤 라벨은 외접 bbox 로 변환한다
- 원본 폴더는 읽기만 한다

사용: python resplit.py <원본 PCB_dataset> <출력 폴더> [--seed 0]
"""
import argparse
import collections
import random
import re
import shutil
from pathlib import Path

NAMES = ['falsecopper', 'missinghole', 'mousebite', 'opencircuit',
         'pinhole', 'scratch', 'shortcircuit', 'spur']
SPLITS = {'train': 0.8, 'val': 0.1, 'test': 0.1}
SRC_SPLITS = ['train', 'valid', 'test']


def base_name(stem):
    stem = re.sub(r'\.rf\.[0-9a-f]+$', '', stem)
    return re.sub(r'_(jpg|jpeg|png)$', '', stem, flags=re.I)


def read_label(path):
    """YOLO 라벨을 읽어 bbox 라인 목록으로 반환. 폴리곤은 bbox 로 변환."""
    out, converted = [], 0
    for line in path.read_text().split('\n'):
        p = line.split()
        if not p:
            continue
        c, v = int(p[0]), [float(x) for x in p[1:]]
        if len(v) != 4:
            xs, ys = v[0::2], v[1::2]
            x0, x1 = max(0.0, min(xs)), min(1.0, max(xs))
            y0, y1 = max(0.0, min(ys)), min(1.0, max(ys))
            v = [(x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0]
            converted += 1
        out.append(f'{c} ' + ' '.join(f'{x:.6f}' for x in v))
    return out, converted


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src', type=Path)
    ap.add_argument('dst', type=Path)
    ap.add_argument('--seed', type=int, default=0)
    args = ap.parse_args()

    # 1) 원본 이미지 단위로 그룹화
    groups = collections.defaultdict(list)  # base -> [(img, label)]
    for sp in SRC_SPLITS:
        for img in sorted((args.src / sp / 'images').iterdir()):
            lbl = args.src / sp / 'labels' / (img.stem + '.txt')
            groups[base_name(img.stem)].append((img, lbl))

    labels, n_conv = {}, 0
    gcount = {}
    for b, items in groups.items():
        cnt = collections.Counter()
        for img, lbl in items:
            lines, k = read_label(lbl) if lbl.exists() else ([], 0)
            labels[img] = lines
            n_conv += k
            cnt.update(int(l.split()[0]) for l in lines)
        gcount[b] = cnt

    # 2) 탐욕적 층화 배정: 큰 그룹부터, 목표 대비 가장 부족한 split 으로
    rng = random.Random(args.seed)
    order = list(groups)
    rng.shuffle(order)
    order.sort(key=lambda b: -len(groups[b]))
    total = collections.Counter()
    for c in gcount.values():
        total.update(c)
    n_total = sum(len(v) for v in groups.values())
    cur = {s: collections.Counter() for s in SPLITS}
    cur_n = {s: 0 for s in SPLITS}
    assign = {}
    for b in order:
        def deficit(s):
            r = SPLITS[s]
            d = r - cur_n[s] / n_total
            for c, k in gcount[b].items():
                d += (r - cur[s][c] / total[c]) * k / max(1, sum(gcount[b].values()))
            return d
        s = max(SPLITS, key=deficit)
        assign[b] = s
        cur[s].update(gcount[b])
        cur_n[s] += len(groups[b])

    # 3) 복사
    if args.dst.exists():
        raise SystemExit(f'{args.dst} 가 이미 있습니다. 지우거나 다른 경로를 지정하세요.')
    for s in SPLITS:
        (args.dst / 'images' / s).mkdir(parents=True)
        (args.dst / 'labels' / s).mkdir(parents=True)
    for b, items in groups.items():
        s = assign[b]
        for img, _ in items:
            shutil.copy2(img, args.dst / 'images' / s / img.name)
            (args.dst / 'labels' / s / (img.stem + '.txt')).write_text(
                '\n'.join(labels[img]) + ('\n' if labels[img] else ''))

    (args.dst / 'data.yaml').write_text(
        f'path: {args.dst.resolve().as_posix()}\n'
        'train: images/train\nval: images/val\ntest: images/test\n\n'
        f'nc: {len(NAMES)}\nnames: {NAMES}\n', encoding='utf-8')
    (args.dst / 'split_groups.csv').write_text(
        'base,split,n_tiles\n' + ''.join(
            f'{b},{assign[b]},{len(groups[b])}\n' for b in sorted(groups)),
        encoding='utf-8')

    # 4) 리포트
    print(f'원본 그룹 {len(groups)}개, 타일 {n_total}장, 폴리곤→bbox 변환 {n_conv}줄')
    print(f'{"class":13s}' + ''.join(f'{s:>14s}' for s in SPLITS))
    for i, n in enumerate(NAMES):
        print(f'{n:13s}' + ''.join(
            f'{cur[s][i]:7d} ({cur[s][i] / total[i]:4.0%})' for s in SPLITS))
    print(f'{"images":13s}' + ''.join(
        f'{cur_n[s]:7d} ({cur_n[s] / n_total:4.0%})' for s in SPLITS))
    print(f'{"groups":13s}' + ''.join(
        f'{sum(1 for v in assign.values() if v == s):14d}' for s in SPLITS))


if __name__ == '__main__':
    main()
