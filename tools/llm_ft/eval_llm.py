"""Evaluate an Ollama model on the held-out SFT eval set (data/sft/mix/eval.jsonl) with automatic, reference-based checks.

Usage (main venv has `ollama`):  python tools/llm_ft/eval_llm.py qwen3:8b --out results/llm/eval_base.json
                                 python tools/llm_ft/eval_llm.py qwen3-defect --out results/llm/eval_tuned.json
Metrics (per task x language): JSON validity, field completeness, language purity (Hangul leaking into vi/en, Latin-only ko), fact fidelity
(each detected type's count and top confidence appear), citation validity (cited [S#] exists; no citation when the gold has none),
refusal accuracy (verdict change / out-of-scope), and similarity to the reference answer.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

import ollama

ROOT = Path(__file__).resolve().parents[2]
HANGUL = re.compile(r"[가-힣]")
VI = re.compile(r"[ăâđêôơưàáạảãằắặẳẵầấậẩẫèéẹẻẽềếệểễìíịỉĩòóọỏõồốộổỗờớợởỡùúụủũừứựửữỳýỵỷỹ]", re.I)
FIELDS = ("summary", "defects", "cause_text", "action_immediate", "action_prevent")


def lang_ok(text: str, lang: str) -> bool:
    if not text:
        return False
    if lang in ("vi", "en"):
        return not HANGUL.search(text) and (lang == "vi" or not VI.search(text))
    return bool(HANGUL.search(text))


def n_refs(system_or_user: str) -> int:
    return len(re.findall(r"^\[S\d+\]", system_or_user, re.M))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--data", default=str(ROOT / "data/sft/mix/eval.jsonl"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    rows = [json.loads(l) for l in open(a.data, encoding="utf-8")]
    if a.limit:
        rows = rows[:a.limit]
    agg = defaultdict(lambda: defaultdict(list))
    samples = []
    for r in rows:
        m = r["messages"]
        key = f'{r["task"]}/{r["lang"]}'
        gold = m[-1]["content"]
        is_json = r["task"] == "report"
        res = ollama.chat(model=a.model, messages=m[:-1], format="json" if is_json else None, think=False,
                          options={"temperature": 0.0, "num_ctx": 6144})
        out = res["message"]["content"].strip()
        ctx = m[0]["content"] + (m[1]["content"] if r["task"] == "report" else "")
        nr = n_refs(ctx)
        cites = re.findall(r"\[S(\d+)\]", out)
        gold_cites = re.findall(r"\[S(\d+)\]", gold)
        A = agg[key]
        A["cite_valid"].append(all(1 <= int(c) <= nr for c in cites))
        A["cite_policy"].append(bool(cites) == bool(gold_cites))      # cite exactly when the gold cites (= when the passage supports it)
        if is_json:
            try:
                obj = json.loads(out)
                A["json_valid"].append(True)
                A["fields_complete"].append(all(obj.get(f) for f in FIELDS[:1] + FIELDS[2:]) and isinstance(obj.get("defects"), list))
                g = json.loads(gold)
                text = json.dumps(obj, ensure_ascii=False)
                facts = g["defects"]
                A["fact_fidelity"].append(statistics.mean(
                    (1.0 if re.search(rf'\b{re.escape(str(re.search(r"(\d\.\d+)", d["description"]).group(1)))}', json.dumps(
                        [x for x in obj.get("defects", []) if isinstance(x, dict) and x.get("type") == d["type"]], ensure_ascii=False)) else 0.0)
                    for d in facts if re.search(r"(\d\.\d+)", d["description"])) if facts else 1.0)
                A["lang_ok"].append(lang_ok(text, r["lang"]))
                A["similarity"].append(difflib.SequenceMatcher(None, " ".join(str(obj.get(k, "")) for k in ("cause_text", "action_immediate", "action_prevent")),
                                                               " ".join(str(g.get(k, "")) for k in ("cause_text", "action_immediate", "action_prevent"))).ratio())
            except (json.JSONDecodeError, AttributeError, TypeError):
                A["json_valid"].append(False)
                A["fields_complete"].append(False)
                A["lang_ok"].append(False)
        else:
            A["lang_ok"].append(lang_ok(out, r["lang"]))
            A["similarity"].append(difflib.SequenceMatcher(None, out, gold).ratio())
            if r["kind"] in ("flip", "oos"):
                A[f'refusal_{r["kind"]}'].append(difflib.SequenceMatcher(None, out, gold).ratio() > 0.6)
        if len(samples) < 6 and r["task"] == "report" and r["lang"] == "vi":
            samples.append({"gold": gold, "pred": out})
    summary = {k: {m: round(statistics.mean(v), 3) for m, v in d.items()} | {"n": len(next(iter(d.values())))} for k, d in sorted(agg.items())}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps({"model": a.model, "summary": summary, "samples": samples}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
