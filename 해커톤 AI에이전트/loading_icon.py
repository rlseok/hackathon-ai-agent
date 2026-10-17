"""처리 중 표시용 애니메이션 SVG: 크고 작은 톱니바퀴 두 개가 맞물려 반대로 돌고, 둘레의 원형 버퍼가 회전한다.

톱니 수 비(10:6)만큼 작은 톱니바퀴가 빨리 돌아 실제로 맞물린 것처럼 보인다. SMIL 애니메이션이라 CSS 배경 그림으로 넣어도 움직인다.
python loading_icon.py 로 실행하면 assets/loading.svg 로도 저장한다 (미리보기용).
"""
import math
from pathlib import Path
from urllib.parse import quote


def _gear_path(cx, cy, r_out, r_root, teeth, hole):
    """톱니바퀴 윤곽(사다리꼴 톱니) + 가운데 구멍 (evenodd)."""
    pts = []
    step = 2 * math.pi / teeth
    for k in range(teeth):
        a = k * step
        for da, r in ((-0.30, r_root), (-0.17, r_out), (0.17, r_out), (0.30, r_root)):
            ang = a + da * step * 1.6
            pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    d = 'M' + ' L'.join(f'{x:.2f} {y:.2f}' for x, y in pts) + ' Z'
    d += (f' M{cx + hole:.2f} {cy:.2f} A{hole} {hole} 0 1 0 {cx - hole:.2f} {cy:.2f}'
          f' A{hole} {hole} 0 1 0 {cx + hole:.2f} {cy:.2f} Z')
    return d


def loading_svg(main='#FF4B4B', second='#9AA0A6', track='rgba(128,128,128,0.25)', period=3.0):
    big = dict(cx=40, cy=57, r_out=24, r_root=18.5, teeth=10, hole=6.5)
    # 두 중심 거리 = 두 피치 반지름의 합 (톱니가 서로의 홈에 들어가게)
    pitch = (big['r_out'] + big['r_root']) / 2 + (14.5 + 10) / 2
    ang = math.radians(-41.5)                                    # 큰 톱니바퀴의 오른쪽 위
    small = dict(cx=round(big['cx'] + pitch * math.cos(ang), 2), cy=round(big['cy'] + pitch * math.sin(ang), 2),
                 r_out=14.5, r_root=10, teeth=6, hole=4)
    small_period = period * small['teeth'] / big['teeth']        # 톱니 수 비율만큼 빨리
    # 처음 각도: 작은 톱니바퀴의 톱니가 큰 톱니바퀴의 홈을 향하게
    to_big = math.degrees(math.atan2(big['cy'] - small['cy'], big['cx'] - small['cx']))
    small_start = round(to_big % (360 / small['teeth']), 2)
    to_small = math.degrees(ang) % 360
    big_start = round((to_small - 180 / big['teeth']) % (360 / big['teeth']), 2)
    return f"""<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'>
<circle cx='50' cy='50' r='45' fill='none' stroke='{track}' stroke-width='5'/>
<circle cx='50' cy='50' r='45' fill='none' stroke='{main}' stroke-width='5' stroke-linecap='round' stroke-dasharray='70 213'>
<animateTransform attributeName='transform' type='rotate' from='0 50 50' to='360 50 50' dur='1s' repeatCount='indefinite'/></circle>
<path fill='{main}' fill-rule='evenodd' d='{_gear_path(**big)}'>
<animateTransform attributeName='transform' type='rotate' from='{big_start} {big["cx"]} {big["cy"]}' to='{big_start + 360} {big["cx"]} {big["cy"]}' dur='{period}s' repeatCount='indefinite'/></path>
<path fill='{second}' fill-rule='evenodd' d='{_gear_path(**small)}'>
<animateTransform attributeName='transform' type='rotate' from='{small_start} {small["cx"]} {small["cy"]}' to='{small_start - 360} {small["cx"]} {small["cy"]}' dur='{small_period}s' repeatCount='indefinite'/></path>
</svg>"""


def loading_data_uri(**kw):
    return 'data:image/svg+xml,' + quote(' '.join(loading_svg(**kw).split()), safe="/:=' ")


if __name__ == '__main__':
    p = Path(__file__).parent / 'assets' / 'loading.svg'
    p.write_text(loading_svg(), encoding='utf-8')
    print('saved', p)
