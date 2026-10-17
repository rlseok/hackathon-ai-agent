// 화면 안내(투어) — 브라우저 안에서만 도는 오버레이.
// tour.py 가 CFG({steps:[{sel,title,body}], labels, dark}) 를 채워 부모 문서에 넣는다.
// 단계를 넘겨도 Streamlit 화면을 다시 그리지 않으며, 강조 영역(spot)과 설명 카드(card)는
// 같은 프레임에서 함께 계산·이동한다 (스크롤·창 크기 변경도 매 프레임 따라감).
(function () {
  const CFG = __CFG__;
  const W = window, D = document;
  if (W.__dtTour) W.__dtTour.destroy();

  const fg = CFG.dark ? '#FAFAFA' : '#262730', bg = CFG.dark ? '#1E1F26' : '#FFFFFF', red = '#FF4B4B';
  const root = D.createElement('div');
  root.id = 'dt-tour';
  root.innerHTML = `<style>
    #dt-tour .dt-spot{position:fixed;left:50%;top:50%;width:0;height:0;border-radius:10px;pointer-events:none;
      box-shadow:0 0 0 200vmax rgba(0,0,0,.55);outline:3px solid ${red};outline-offset:3px;z-index:999998}
    #dt-tour .dt-spot.dt-none{outline-color:transparent}
    #dt-tour .dt-card{position:fixed;left:50%;top:50%;width:min(420px,90vw);box-sizing:border-box;z-index:999999;
      background:${bg};color:${fg};border:2px solid ${red};border-radius:12px;padding:14px 18px 12px;
      box-shadow:0 10px 40px rgba(0,0,0,.45);font-family:"Source Sans Pro",sans-serif;font-size:15px;line-height:1.5}
    #dt-tour.dt-anim .dt-spot,#dt-tour.dt-anim .dt-card{transition:left .35s ease,top .35s ease,width .35s ease,height .35s ease}
    #dt-tour .dt-step{font-size:12px;opacity:.7;margin-bottom:2px}
    #dt-tour .dt-title{font-size:19px;font-weight:700;margin:2px 0 6px}
    #dt-tour .dt-body{margin-bottom:12px}
    #dt-tour .dt-btns{display:flex;gap:8px}
    #dt-tour button{flex:1;padding:7px 10px;border-radius:8px;border:1px solid rgba(128,128,128,.45);
      background:transparent;color:${fg};cursor:pointer;font-size:14px}
    #dt-tour button.dt-next{background:${red};border-color:${red};color:#fff;font-weight:600}
    #dt-tour button:disabled{opacity:.35;cursor:default}
    #dt-tour .dt-dots{display:flex;gap:4px;justify-content:center;margin-top:10px}
    #dt-tour .dt-dots i{width:6px;height:6px;border-radius:3px;background:rgba(128,128,128,.45)}
    #dt-tour .dt-dots i.on{background:${red};width:16px}
  </style>
  <div class="dt-spot dt-none"></div>
  <div class="dt-card">
    <div class="dt-step"></div><div class="dt-title"></div><div class="dt-body"></div>
    <div class="dt-btns"><button class="dt-back"></button><button class="dt-next"></button><button class="dt-skip"></button></div>
    <div class="dt-dots"></div>
  </div>`;
  D.body.appendChild(root);

  const spot = root.querySelector('.dt-spot'), card = root.querySelector('.dt-card');
  const $ = s => root.querySelector(s);
  const M = 14, GAP = 18, PAD = 6;
  let i = 0, raf = 0, animUntil = 0, last = '';

  function target() {
    const sel = CFG.steps[i].sel;
    if (!sel) return null;
    const el = D.querySelector(sel);
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return r.width > 2 && r.height > 2 ? {el, r} : null;
  }

  function show(dir) {
    const s = CFG.steps[i], n = CFG.steps.length;
    $('.dt-step').textContent = `${CFG.labels.step} ${i + 1} / ${n}`;
    $('.dt-title').innerHTML = s.title;
    $('.dt-body').innerHTML = s.body;
    $('.dt-back').textContent = CFG.labels.back;
    $('.dt-back').disabled = i === 0;
    $('.dt-next').textContent = i === n - 1 ? CFG.labels.finish : CFG.labels.next;
    $('.dt-skip').textContent = CFG.labels.skip;
    $('.dt-skip').style.display = i === n - 1 ? 'none' : '';
    $('.dt-dots').innerHTML = CFG.steps.map((_, k) => `<i class="${k === i ? 'on' : ''}"></i>`).join('');
    root.classList.add('dt-anim');                 // 단계가 바뀔 때만 부드럽게 이동
    animUntil = performance.now() + 420;
    const t = target();
    const off = r => r.top < 70 || r.bottom > W.innerHeight;
    if (t && off(t.r)) {
      const block = t.r.height > W.innerHeight * 0.6 ? 'start' : 'center';
      unstick(t.el);
      t.el.scrollIntoView({block, behavior: 'smooth'});
      const step = i;                              // 부드러운 스크롤이 안 끝났으면 바로 이동
      setTimeout(() => {
        const u = target();
        if (step === i && u && (u.r.bottom < 0 || u.r.top > W.innerHeight)) { unstick(u.el); u.el.scrollIntoView({block}); }
      }, 700);
    }
    update();                                      // 탭이 백그라운드라 프레임이 멈춰도 자리를 잡도록 직접도 부른다
    [120, 300, 500, 800].forEach(ms => setTimeout(update, ms));
  }

  // 채팅 입력창이 있는 화면은 Streamlit 이 페이지를 맨 아래에 붙여 둔다 (stAppScrollToBottomContainer).
  // 위로 스크롤하는 휠 신호를 먼저 보내 그 고정을 풀어야 위쪽 영역으로 스크롤한 위치가 유지된다.
  function unstick(el) {
    const box = el.closest('[data-testid="stAppScrollToBottomContainer"]');
    if (box) box.dispatchEvent(new WheelEvent('wheel', {deltaY: -120, bubbles: true, cancelable: true}));
  }

  function bestSpot(r, cw, ch, vw, vh) {
    const cT = t => Math.max(M, Math.min(t, vh - ch - M)), cL = l => Math.max(M, Math.min(l, vw - cw - M));
    const cands = [[r.right + GAP, r.top], [r.left - GAP - cw, r.top], [r.left, r.bottom + GAP], [r.left, r.top - GAP - ch],
                   [vw, vh], [vw, 0], [0, vh], [0, 0]].map(([l, t]) => [cL(l), cT(t)]);
    const cover = ([l, t]) => Math.max(0, Math.min(l + cw, r.right) - Math.max(l, r.left)) *
                              Math.max(0, Math.min(t + ch, r.bottom) - Math.max(t, r.top));
    let best = cands[0], bc = Infinity;
    for (const c of cands) { const v = cover(c); if (v < bc) { best = c; bc = v; } if (v === 0) break; }
    return best;
  }

  function update() {                             // spot 과 card 를 같은 기준으로 한 번에 계산
    const vw = W.innerWidth, vh = W.innerHeight, cw = card.offsetWidth, ch = card.offsetHeight;
    const t = target();
    let sl, st, sw, sh, cl, ct;
    if (t) {
      const r = t.r;
      sl = r.left - PAD; st = r.top - PAD; sw = r.width + PAD * 2; sh = r.height + PAD * 2;
      [cl, ct] = bestSpot({left: sl, top: st, right: sl + sw, bottom: st + sh}, cw, ch, vw, vh);
    } else {
      sl = vw / 2; st = vh / 2; sw = 0; sh = 0;
      cl = (vw - cw) / 2; ct = (vh - ch) / 2;
    }
    const key = [sl, st, sw, sh, cl, ct].map(v => Math.round(v)).join(',');
    if (key !== last) {                           // 바뀐 것이 있을 때만 쓴다
      last = key;
      Object.assign(spot.style, {left: sl + 'px', top: st + 'px', width: sw + 'px', height: sh + 'px'});
      spot.classList.toggle('dt-none', !t);
      Object.assign(card.style, {left: cl + 'px', top: ct + 'px'});
    }
    if (animUntil && performance.now() > animUntil) { root.classList.remove('dt-anim'); animUntil = 0; }
  }
  function frame() { update(); raf = W.requestAnimationFrame(frame); }   // 화면이 보일 때는 매 프레임 따라감
  const onMove = () => update();

  function go(k) { i = Math.max(0, Math.min(CFG.steps.length - 1, k)); show(); }
  function onKey(e) {
    if (e.key === 'Escape') destroy();
    else if (e.key === 'ArrowRight') { i === CFG.steps.length - 1 ? destroy() : go(i + 1); }
    else if (e.key === 'ArrowLeft') go(i - 1);
  }
  function destroy() {
    W.cancelAnimationFrame(raf);
    D.removeEventListener('keydown', onKey, true);
    D.removeEventListener('scroll', onMove, true);
    W.removeEventListener('resize', onMove);
    root.remove();
    W.__dtTour = null;
  }

  $('.dt-back').onclick = () => go(i - 1);
  $('.dt-next').onclick = () => (i === CFG.steps.length - 1 ? destroy() : go(i + 1));
  $('.dt-skip').onclick = destroy;
  D.addEventListener('keydown', onKey, true);
  D.addEventListener('scroll', onMove, true);
  W.addEventListener('resize', onMove);
  W.__dtTour = {destroy};
  show();
  frame();
})();
