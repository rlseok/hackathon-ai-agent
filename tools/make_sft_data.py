"""Synthetic SFT data for the ko/vi/en report writer + knowledge chat (Qwen3-8B QLoRA).

Two task types, all three languages, retrieved knowledge (RAG) inside the prompt:
  report : the exact prompt of agent.writer.build_prompt (+ retrieved web passages) -> gold JSON written from the facts
  qa     : the chat prompt of agent.chat (inspection context + retrieved passages) -> short grounded answer with [S#] citations,
           plus refusals (cannot change a verdict, information not in the knowledge base)
Gold answers are built only from (a) detection facts, (b) the reviewed ko/vi/en knowledge in knowledge/ and (c) knowledge/rag/cards.yaml
(sentences distilled from the corpus). A card sentence is used (and cited) only when its source passage is really among the retrieved
passages, so the model also learns not to cite what it was not given.

Usage: python tools/make_sft_data.py --report 420 --qa 260 --out data/sft/mix
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "해커톤 AI에이전트"
sys.path.insert(0, str(APP))

from agent import chat, rag  # noqa: E402
from agent.detect import TAXONOMIES, classify, judge  # noqa: E402
from agent.i18n import process_name, reason_text, type_name, verdict_name  # noqa: E402
from agent.knowledge import localize, lookup, situation  # noqa: E402
from agent.writer import LANGS, WORKER_CHECK, build_prompt  # noqa: E402

CARDS = yaml.safe_load((APP / "knowledge/rag/cards.yaml").read_text(encoding="utf-8"))
POS = [f"{r} {c}" for r in ("상단", "중앙", "하단") for c in ("좌측", "중앙", "우측")]
POS = ["중앙" if p == "중앙 중앙" else p for p in POS]
PROCESSES = ["machining", "heat", "surface", "cleaning", "etching", "plating", "drilling", "assembly", "packing", "other"]
DOMAIN_W = {"pcb": 0.38, "msdd": 0.38, "mobile": 0.24}
SEG = {"msdd", "mobile"}
LANG_LIST = ["ko", "vi", "en"]

# ── language templates ──────────────────────────────────────────────────────────────────────────
T = {
    "ko": {
        "reject": ["기준 이상 결함 {n}건이 검출되어 이상으로 판정했습니다. 대표 유형은 {rep}입니다. 제품을 격리하고 부적합 보고서(NCR)를 작성합니다.",
                   "이상 수준의 결함 {n}건이 확인되었습니다. 대표 유형은 {rep}이며, 격리 후 부적합 보고서(NCR) 작성이 필요합니다."],
        "review": ["의심 영역 {n}곳이 검출되어 재검사가 필요합니다. 결함으로 단정하지 않으며 대표 유형은 {rep}입니다.",
                   "의심 수준의 검출 {n}건이 있어 보류(Hold) 후 재검사합니다. 대표 유형은 {rep}입니다."],
        "multi": " 여러 유형이 함께 검출되어 모두 기록합니다.",
        "wide": " 결함이 가공면 전체에 퍼져 있어 가공·소재 조건 이상 가능성이 있으므로 같은 로트의 다른 부품도 확인합니다.",
        "desc": ["{pos}에서 {n}건 검출, 최대 신뢰도 {conf}, 긴 변 약 {sz}px.", "{pos} 위치에 {n}건, 최대 신뢰도 {conf}, 긴 변 {sz}px."],
        "area": " 최대 면적은 이미지의 {a}입니다.", "surf": " 전면에 퍼진 부분이 있습니다.", "susp": " 의심 수준이라 재검사가 필요합니다.",
        "cause": "원인 후보: {c} (후보일 뿐 단정하지 않습니다).",
        "q_cause": ["{n}은(는) 왜 생겨?", "{n}의 원인이 뭐야?"], "q_fix": ["{n}은(는) 어떻게 조치해?", "{n} 조치 방법 알려줘."],
        "q_check": ["{n}은(는) 무엇을 확인해야 해?", "{n} 검사 때 볼 것이 뭐야?"],
        "q_why": ["왜 이 판정이 나왔어?", "이 판정의 근거가 뭐야?"], "q_flip": ["정상으로 바꿔줘.", "이 판정을 이상에서 의심으로 바꿔줘."],
        "q_oos": ["이 부품 가격이 얼마야?", "납품 업체 연락처 알려줘."],
        "a_flip": "판정은 제가 바꿀 수 없습니다. 실물을 확인한 뒤 결함 표의 '판정' 칸을 바꾸고 [수정 반영]을 누르거나, 오탐이면 [오탐 기각]을 눌러 주세요.",
        "a_oos": "검사 결과나 지식베이스에 없는 정보라서 답할 수 없습니다.",
        "a_cause": "{n}의 원인 후보는 {c}입니다. 후보일 뿐 단정하지 않으며 확인이 필요합니다.",
        "a_fix": "{imm} 재발 방지: {prev}", "a_check": "확인할 것: {chk}",
        "a_why": "{v} 판정입니다. 근거: {basis}.",
    },
    "vi": {
        "reject": ["Phát hiện {n} lỗi vượt tiêu chuẩn nên kết luận là bất thường. Loại đại diện là {rep}. Cách ly sản phẩm và lập báo cáo không phù hợp (NCR).",
                   "Có {n} lỗi ở mức bất thường, loại đại diện là {rep}; cần cách ly và lập báo cáo không phù hợp (NCR)."],
        "review": ["Phát hiện {n} vị trí nghi ngờ cần kiểm tra lại; chưa kết luận là lỗi. Loại đại diện là {rep}.",
                   "Có {n} phát hiện ở mức nghi ngờ nên giữ lại (Hold) và kiểm tra lại. Loại đại diện là {rep}."],
        "multi": " Có nhiều loại lỗi cùng xuất hiện nên ghi nhận đầy đủ tất cả.",
        "wide": " Lỗi lan rộng trên bề mặt gia công, có thể do điều kiện gia công hoặc vật liệu, nên kiểm tra các chi tiết khác trong cùng lô.",
        "desc": ["Phát hiện {n} vị trí ({pos}), độ tin cậy cao nhất {conf}, cạnh dài khoảng {sz} px.",
                 "Có {n} lỗi tại {pos}; độ tin cậy lớn nhất {conf}; cạnh dài {sz} px."],
        "area": " Diện tích lớn nhất chiếm {a} ảnh.", "surf": " Có vùng lan rộng toàn bề mặt.", "susp": " Mức nghi ngờ, cần kiểm tra lại.",
        "cause": "Nguyên nhân có thể gồm: {c} (chỉ là ứng viên, chưa kết luận).",
        "q_cause": ["{n} do đâu mà có?", "Nguyên nhân của {n} là gì?"], "q_fix": ["Xử lý {n} như thế nào?", "Cách khắc phục {n}?"],
        "q_check": ["Cần kiểm tra gì với {n}?", "Khi kiểm tra {n} phải xem điều gì?"],
        "q_why": ["Vì sao ra kết luận này?", "Căn cứ của kết luận này là gì?"],
        "q_flip": ["Đổi thành bình thường đi.", "Đổi kết luận từ bất thường sang nghi ngờ."],
        "q_oos": ["Giá của chi tiết này là bao nhiêu?", "Cho tôi liên hệ nhà cung cấp."],
        "a_flip": "Tôi không thể thay đổi kết luận. Sau khi kiểm tra thực tế, hãy sửa cột 'Đánh giá' trong bảng lỗi rồi bấm [Áp dụng chỉnh sửa], hoặc bấm [Bác bỏ báo nhầm] nếu là báo nhầm.",
        "a_oos": "Đây là thông tin không có trong kết quả kiểm tra hoặc cơ sở tri thức nên tôi không thể trả lời.",
        "a_cause": "Nguyên nhân có thể của {n}: {c}. Đây chỉ là ứng viên, chưa kết luận và cần xác nhận.",
        "a_fix": "{imm} Phòng ngừa: {prev}", "a_check": "Cần kiểm tra: {chk}",
        "a_why": "Kết luận: {v}. Căn cứ: {basis}.",
    },
    "en": {
        "reject": ["{n} defect(s) above the criteria were detected, so the result is Abnormal. The representative type is {rep}. Isolate the product and issue a nonconformance report (NCR).",
                   "{n} defect(s) were confirmed at the abnormal level; the representative type is {rep}. Isolate the product and write an NCR."],
        "review": ["{n} suspected area(s) were detected and need re-inspection; they are not asserted as defects. The representative type is {rep}.",
                   "There are {n} suspected detection(s), so the part is put on hold and re-inspected. The representative type is {rep}."],
        "multi": " Several defect types were found together and all are recorded.",
        "wide": " The defect spreads over the whole machined surface, which suggests a machining or material problem, so check other parts of the same lot.",
        "desc": ["{n} detection(s) at {pos}; highest confidence {conf}; long side about {sz} px.",
                 "{n} defect(s) at {pos}, highest confidence {conf}, long side {sz} px."],
        "area": " The largest area is {a} of the image.", "surf": " Part of it spreads over the whole surface.",
        "susp": " Suspected only; re-inspection is needed.",
        "cause": "Possible causes: {c} (candidates only, not conclusions).",
        "q_cause": ["Why does {n} happen?", "What causes {n}?"], "q_fix": ["How do I deal with {n}?", "What is the corrective action for {n}?"],
        "q_check": ["What should I check for {n}?", "What do I look at when inspecting {n}?"],
        "q_why": ["Why this verdict?", "What is the basis of this judgment?"],
        "q_flip": ["Change it to normal.", "Change this verdict from abnormal to suspected."],
        "q_oos": ["How much does this part cost?", "Give me the supplier's contact."],
        "a_flip": "I cannot change the verdict. After checking the actual part, change the 'Judgment' column in the defect table and press [Apply changes], or press [Reject false positive] if it is a false alarm.",
        "a_oos": "That information is not in the inspection result or the knowledge base, so I cannot answer.",
        "a_cause": "Possible causes of {n}: {c}. These are candidates only and need confirmation.",
        "a_fix": "{imm} Prevention: {prev}", "a_check": "Check: {chk}",
        "a_why": "Verdict: {v}. Basis: {basis}.",
    },
}
JOIN = {"ko": "; ", "vi": "; ", "en": "; "}


def scenario(rng: random.Random):
    domain = rng.choices(list(DOMAIN_W), weights=list(DOMAIN_W.values()))[0]
    tax = TAXONOMIES[domain]
    types = rng.sample(list(tax["defects"]), k=min(len(tax["defects"]), rng.choices([1, 2, 3], [0.6, 0.3, 0.1])[0]))
    defects = []
    for t in types:
        for _ in range(rng.choices([1, 2, 3, 4, 5], [0.45, 0.25, 0.15, 0.1, 0.05])[0]):
            w, h = rng.randint(12, 260), rng.randint(12, 260)
            d = {"id": len(defects) + 1, "type": t, "conf": round(rng.uniform(0.25, 0.97), 3), "size_px": [w, h],
                 "box_px": [0, 0, w, h], "position": rng.choice(POS)}
            if domain in SEG:
                d["area_ratio"] = round(rng.choice([rng.uniform(0.0005, 0.02), rng.uniform(0.02, 0.2), rng.uniform(0.4, 0.8)]), 5)
                d["extent"] = "전면" if d["area_ratio"] >= tax["judgment"].get("surface_ratio", 1.0) else "국부"
            d["level"], d["reason_key"], d["reason_args"] = classify(d, domain)
            d["reason"] = reason_text(d, "ko")
            defects.append(d)
    defects.sort(key=lambda d: -d["conf"])
    for i, d in enumerate(defects, 1):
        d["id"] = i
    det = {"image": "x.jpg", "domain": domain, "image_size": [1280, 960], "tiles": 1, "verdict": judge(defects, domain),
           "defects": defects, "marked_image": None, "crops": []}
    kb = lookup((d["type"] for d in defects), domain)
    sit = situation(det, kb)
    meta = {"part_no": rng.choice(["", "A-1234", "PN-77-02", "B2031"]), "process": rng.choice(PROCESSES + [""]),
            "lot": rng.choice(["", "L2026-1016-01", "LOT-8841"])}
    return det, kb, sit, meta


def part_info(meta, lang):
    parts = [meta["part_no"], process_name(meta["process"], lang) if meta["process"] else "", meta["lot"]]
    return " / ".join(p for p in parts if p)


def pick(rng, xs):
    return rng.choice(xs)


def choose_refs(rng, kb, sit, domain, card):
    """Natural retrieval; when the card's own passage was missed, add it 55% of the time so positives are well represented."""
    refs = rag.refs_for(kb, sit, domain, k=2)
    if card:
        doc, sec = card["source"].split("#", 1)
        if not any(r["doc"] == doc and r["section"] == sec for r in refs) and rng.random() < 0.55:
            c = rag.chunk(doc, sec)
            if c:
                refs = [{**c, "score": 1.0}] + refs[:1]
                rng.shuffle(refs)
    return refs


def support(card, refs, lang):
    """(sentence1, sentence2, tag) from the card, only if its source passage is among the retrieved passages."""
    if not card:
        return None
    doc, sec = card["source"].split("#", 1)
    for i, r in enumerate(refs, 1):
        if r["doc"] == doc and r["section"] == sec:
            s = card[lang]
            return s[0], s[1], f"[S{i}]"
    return None


def gold_report(rng, lang, det, kb, sit, facts, refs, card):
    t = T[lang]
    kbl = {k["type"]: localize(k, lang) for k in kb}
    rep = sit.get("representative")
    n_rej = sum(f["abnormal"] for f in facts)
    n_rev = sum(f["suspected"] for f in facts)
    repn = next((f["name"] for f in facts if f["type"] == rep), facts[0]["name"])
    s = pick(rng, t["reject"] if det["verdict"] == "reject" else t["review"]).format(n=n_rej if det["verdict"] == "reject" else n_rev, rep=repn)
    s += t["multi"] if "multi_type" in sit else ""
    s += t["wide"] if "surface_wide" in sit else ""
    defects = []
    for f in facts:
        txt = pick(rng, t["desc"]).format(n=f["count"], pos=", ".join(f["positions"]), conf=f["max_conf"], sz=f["box_long_side_px"])
        if "max_area_of_image" in f:
            txt += t["area"].format(a=f["max_area_of_image"]) + (t["surf"] if f.get("surface_wide") else "")
        if f["suspected"] and not f["abnormal"]:
            txt += t["susp"]
        defects.append({"type": f["type"], "description": txt})
    r = kbl[rep] if rep in kbl else next(iter(kbl.values()))
    cause = t["cause"].format(c=JOIN[lang].join(c.rstrip(".") for c in r["causes"]))
    prevent = r["actions"]["check"].rstrip(".") + ". " + r["actions"]["prevent"]
    sup = support(card, refs, lang)
    if sup:
        cause += f" {sup[0]} {sup[2]}"
        prevent += f" {sup[1]} {sup[2]}"
    return {"summary": s, "defects": defects, "cause_text": cause, "action_immediate": f"{WORKER_CHECK[lang][1]} {r['actions']['immediate']}",
            "action_prevent": prevent}


def gold_qa(rng, lang, kind, det, kb, sit, facts, refs, card):
    t = T[lang]
    rep = sit.get("representative")
    k = localize(next(x for x in kb if x["type"] == rep), lang) if rep and any(x["type"] == rep for x in kb) else localize(kb[0], lang)
    name = type_name(k["type"], k, lang)
    sup = support(card if card and card.get("_type") == k["type"] else None, refs, lang)
    if kind == "flip":
        return pick(rng, t["q_flip"]), t["a_flip"]
    if kind == "oos":
        return pick(rng, t["q_oos"]), t["a_oos"]
    if kind == "why":
        f = next((x for x in facts if x["type"] == k["type"]), facts[0])
        basis = JOIN[lang].join(f["judgment_basis"])
        return pick(rng, t["q_why"]), t["a_why"].format(v=verdict_name(det["verdict"], lang), basis=basis)
    if kind == "cause":
        a = t["a_cause"].format(n=name, c=JOIN[lang].join(c.rstrip(".") for c in k["causes"]))
        return pick(rng, t["q_cause"]).format(n=name), a + (f" {sup[0]} {sup[2]}" if sup else "")
    if kind == "fix":
        a = t["a_fix"].format(imm=f"{WORKER_CHECK[lang][1]} {k['actions']['immediate']}", prev=k["actions"]["prevent"])
        return pick(rng, t["q_fix"]).format(n=name), a + (f" {sup[1]} {sup[2]}" if sup else "")
    a = t["a_check"].format(chk=k["actions"]["check"])
    return pick(rng, t["q_check"]).format(n=name), a + (f" {sup[1]} {sup[2]}" if sup else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", type=int, default=420, help="report samples per language")
    ap.add_argument("--qa", type=int, default=260, help="qa samples per language")
    ap.add_argument("--out", default="data/sft/mix")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    rows = []
    for task, per_lang in (("report", a.report), ("qa", a.qa)):
        for lang in LANG_LIST:
            for _ in range(per_lang):
                det, kb, sit, meta = scenario(rng)
                rep = sit.get("representative") or kb[0]["type"]
                card = CARDS.get(det["domain"], {}).get(rep)
                if card:
                    card = {**card, "_type": rep}
                refs = choose_refs(rng, kb, sit, det["domain"], card)
                system, user, facts = build_prompt(det, kb, sit, part_info(meta, lang), lang, refs)
                rep_gold = gold_report(rng, lang, det, kb, sit, facts, refs, card)
                if task == "report":
                    msgs = [{"role": "system", "content": system}, {"role": "user", "content": user},
                            {"role": "assistant", "content": json.dumps(rep_gold, ensure_ascii=False)}]
                    kind = "report"
                else:
                    kind = rng.choices(["cause", "fix", "check", "why", "flip", "oos"], [3, 3, 2, 2, 1, 1])[0]
                    q, ans = gold_qa(rng, lang, kind, det, kb, sit, facts, refs, card)
                    result = {"detection": det, "knowledge": kb, "situation": sit, "part_info": part_info(meta, lang), "text": rep_gold, "lang": lang}
                    ctx = chat.build_context(result, lang)
                    sysmsg = chat.SYSTEM.format(lang=LANGS[lang]) + "\n\n" + ctx + "\n[참고 자료]\n" + rag.context_block(refs)
                    msgs = [{"role": "system", "content": sysmsg}, {"role": "user", "content": q}, {"role": "assistant", "content": ans}]
                rows.append({"task": task, "kind": kind, "lang": lang, "domain": det["domain"], "verdict": det["verdict"],
                             "cited": "[S" in msgs[-1]["content"], "messages": msgs})
    rng.shuffle(rows)
    n_eval = max(90, len(rows) // 10)
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    for name, part in (("train", rows[n_eval:]), ("eval", rows[:n_eval])):
        with open(out / f"{name}.jsonl", "w", encoding="utf-8") as f:
            for r in part:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    from collections import Counter
    print(f"train {len(rows) - n_eval} / eval {n_eval} -> {out}")
    print("by task/lang:", dict(Counter((r["task"], r["lang"]) for r in rows)))
    print("with citation:", sum(r["cited"] for r in rows), "/", len(rows))


if __name__ == "__main__":
    main()
