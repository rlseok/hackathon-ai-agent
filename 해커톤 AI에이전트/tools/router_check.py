"""라우터 → 검출 연결 점검 (LLM 없이): 각 도메인 test 사진을 pipeline.pick_domain 으로 분류하고 알맞은 YOLO 모델로 검출까지 돌린다.

사용: python tools/router_check.py [--n 20]   (패키지 폴더에서)
"""
import argparse
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / 'tools'))
from agent import pipeline  # noqa: E402
from agent.detect import detect  # noqa: E402
from agent.router import DomainUncertain  # noqa: E402
from router_data import SOURCES, files  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=20)
    a = ap.parse_args()
    ok = tot = unsure = 0
    for dom, (base, sub) in SOURCES.items():
        imgs = files(base / sub['test'])[::max(1, len(files(base / sub['test'])) // a.n)][:a.n]
        got, dets, t_route = Counter(), 0, 0.0
        for p in imgs:
            t0 = time.time()
            try:
                d, route = pipeline.pick_domain([p])
            except DomainUncertain:
                unsure += 1
                got['uncertain'] += 1
                continue
            t_route += time.time() - t0
            got[d] += 1
            dets += len(detect(p, d)['defects'])
        ok += got[dom]
        tot += len(imgs)
        print(f'{dom:7s} {len(imgs):3d}장 → {dict(got)}  검출 합계 {dets}  라우팅 평균 {1000 * t_route / max(1, len(imgs)):.0f} ms')
    print(f'자동 분류 정답 {ok}/{tot}, 불확실 {unsure}')


if __name__ == '__main__':
    main()
