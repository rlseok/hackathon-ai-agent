"""추가 데이터셋(PCB_Project v8 등)을 클래스 재매핑해 pcb_v2 에 합친 새 데이터셋을 만든다.

- 클래스 이름으로 기존 번호에 재매핑한다 (순서가 달라도 안전)
- 같은 원본 이미지(base)가 기존 split_groups.csv 에서 val/test 에 속하면 추가하지 않는다 (누수 방지)
  기존에 없는 새 원본은 train 에 넣는다
- val/test 는 기존과 동일하게 유지해 이전 모델과 공정하게 비교할 수 있게 한다

사용: python merge_extra.py <기존 pcb_v2> <추가 데이터셋 split 폴더(images, labels)> <추가 data.yaml> <출력 폴더> --prefix v8_
"""
import argparse
import collections
import csv
import shutil
from pathlib import Path

import yaml

from resplit import base_name

# 추가 데이터셋 클래스명 -> 기존 클래스명
ALIASES = {
    'pinhole': 'pinhole', 'scratch': 'scratch', 'missing_hole': 'missinghole',
    'mouse_bite': 'mousebite', 'open_circuit': 'opencircuit', 'short': 'shortcircuit',
    'spur': 'spur', 'spurious_copper': 'falsecopper',
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('base', type=Path)
    ap.add_argument('extra', type=Path)
    ap.add_argument('extra_yaml', type=Path)
    ap.add_argument('dst', type=Path)
    ap.add_argument('--prefix', default='extra_')
    args = ap.parse_args()

    base_yaml = yaml.safe_load((args.base / 'data.yaml').read_text(encoding='utf-8'))
    names = base_yaml['names']
    extra_names = yaml.safe_load(args.extra_yaml.read_text(encoding='utf-8'))['names']
    remap = {i: names.index(ALIASES[n.lower()]) for i, n in enumerate(extra_names)}
    print('class remap:', {f'{extra_names[k]}({k})': f'{names[v]}({v})' for k, v in remap.items()})

    split_of = {r['base']: r['split'] for r in
                csv.DictReader(open(args.base / 'split_groups.csv', encoding='utf-8'))}

    if args.dst.exists():
        raise SystemExit(f'{args.dst} 가 이미 있습니다. 지우거나 다른 경로를 지정하세요.')
    print('copying base dataset...')
    shutil.copytree(args.base / 'images', args.dst / 'images')
    shutil.copytree(args.base / 'labels', args.dst / 'labels',
                    ignore=shutil.ignore_patterns('*.cache'))

    added, skipped = collections.Counter(), collections.Counter()
    for img in sorted((args.extra / 'images').iterdir()):
        b = base_name(img.stem)
        s = split_of.get(b, 'train')
        if s != 'train':
            skipped[s] += 1
            continue
        lines = []
        for line in (args.extra / 'labels' / (img.stem + '.txt')).read_text().splitlines():
            p = line.split()
            if p:
                c = remap[int(p[0])]
                lines.append(' '.join([str(c)] + p[1:]))
                added[c] += 1
        name = args.prefix + img.name
        shutil.copy2(img, args.dst / 'images' / 'train' / name)
        (args.dst / 'labels' / 'train' / (Path(name).stem + '.txt')).write_text(
            '\n'.join(lines) + ('\n' if lines else ''))
        added['images'] += 1

    (args.dst / 'data.yaml').write_text(
        f'path: {args.dst.resolve().as_posix()}\n'
        'train: images/train\nval: images/val\ntest: images/test\n\n'
        f'nc: {len(names)}\nnames: {names}\n', encoding='utf-8')
    shutil.copy2(args.base / 'split_groups.csv', args.dst / 'split_groups.csv')

    print(f'added to train: {added["images"]} images, skipped (val/test 원본과 겹침): {dict(skipped)}')
    for i, n in enumerate(names):
        print(f'  {n:13s} +{added[i]} boxes')
    print('train images now:', len(list((args.dst / 'images' / 'train').iterdir())))


if __name__ == '__main__':
    main()
