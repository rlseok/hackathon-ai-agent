"""Audit a YOLO-format dataset (detect or segment): label sanity, class balance, duplicates and cross-split leakage.

Usage: python tools/audit_dataset.py msdd
Checks: malformed/out-of-range/degenerate labels, duplicate labels, empty-label share, box-size distribution per class,
exact + near-duplicate images (64-bit difference hash, Hamming <= 4) inside a split and ACROSS splits (= leakage).
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CFG = {
    "msdd": {"root": ROOT / "data/huggingface/metal-surface-defect-v1",
             "splits": {"train": ("images/train", "labels/train"), "val": ("images/val", "labels/val"),
                        "test": ("images/test", "labels/test")},
             "names": ["Dark Spot", "Fold", "Oxidation", "Porosity", "Scratch", "Stain"]},
}
POP = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)


def dhash(path: Path) -> np.uint64:
    im = Image.open(path).convert("L").resize((9, 8), Image.LANCZOS)
    a = np.asarray(im, dtype=np.int16)
    bits = (a[:, 1:] > a[:, :-1]).flatten().astype(np.uint8)
    return np.packbits(bits).view(np.uint64)[0]


def hamming(h: np.uint64, hs: np.ndarray) -> np.ndarray:
    x = (hs ^ h).view(np.uint8).reshape(len(hs), 8)
    return POP[x].sum(1)


def parse(path: Path):
    rows, bad = [], 0
    if not path.exists():
        return rows, 0
    for line in path.read_text().splitlines():
        p = line.split()
        if not p:
            continue
        try:
            c, v = int(p[0]), [float(x) for x in p[1:]]
        except ValueError:
            bad += 1
            continue
        if len(v) == 4 or (len(v) >= 6 and len(v) % 2 == 0):
            rows.append((c, v))
        else:
            bad += 1
    return rows, bad


def box_of(v):
    if len(v) == 4:
        return v[0] - v[2] / 2, v[1] - v[3] / 2, v[0] + v[2] / 2, v[1] + v[3] / 2
    xs, ys = v[0::2], v[1::2]
    return min(xs), min(ys), max(xs), max(ys)


def main():
    cfg = CFG[sys.argv[1]]
    names = cfg["names"]
    out = {"dataset": sys.argv[1], "splits": {}}
    keys, hs_list = [], []
    for split, (imd, lbd) in cfg["splits"].items():
        imgs = sorted(p for p in (cfg["root"] / imd).iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
        cls, n_box, empty, bad, oob, tiny, dup_lab, missing = Counter(), 0, 0, 0, 0, 0, 0, 0
        areas = defaultdict(list)
        for p in imgs:
            lab = cfg["root"] / lbd / f"{p.stem}.txt"
            missing += not lab.exists()
            rows, b = parse(lab)
            bad += b
            empty += not rows
            seen = set()
            for c, v in rows:
                x0, y0, x1, y1 = box_of(v)
                n_box += 1
                cls[names[c]] += 1
                oob += min(v) < -1e-6 or max(v) > 1 + 1e-6
                areas[names[c]].append(max(0, x1 - x0) * max(0, y1 - y0))
                tiny += (x1 - x0) < 0.01 or (y1 - y0) < 0.01
                key = (c, tuple(round(x, 4) for x in v))
                dup_lab += key in seen
                seen.add(key)
            keys.append((split, p.name))
            hs_list.append(dhash(p))
        out["splits"][split] = {
            "images": len(imgs), "boxes": n_box, "empty_label_images": empty, "missing_label_files": missing,
            "malformed_lines": bad, "out_of_range": oob, "tiny_boxes_lt_1pct_side": tiny, "duplicate_labels": dup_lab,
            "class_counts": dict(cls),
            "box_area_median_pct": {k: round(100 * float(np.median(v)), 2) for k, v in areas.items()}}
    hs = np.array(hs_list, dtype=np.uint64)
    split_of = np.array([k[0] for k in keys])
    exact = len(hs) - len(set(hs.tolist()))
    near_same = Counter()
    near_cross = Counter()
    has_near = np.zeros(len(hs), bool)
    for i in range(len(hs)):
        d = hamming(hs[i], hs)
        d[i] = 99
        for j in np.where(d <= 4)[0]:
            has_near[i] = True
            if split_of[i] == split_of[j]:
                near_same[split_of[i]] += 1
            else:
                near_cross["-".join(sorted((split_of[i], split_of[j])))] += 1
    out["duplicates"] = {
        "images_sharing_exact_hash_beyond_first": int(exact),
        "images_with_near_duplicate_in_same_split": {s: int(((split_of == s) & has_near).sum()) for s in cfg["splits"]},
        "near_duplicate_pair_counts_across_splits": {k: v // 2 for k, v in near_cross.items()},
    }
    train_h = hs[split_of == "train"]
    leak = {}
    for s in ("val", "test"):
        idx = np.where(split_of == s)[0]
        n = sum(1 for i in idx if hamming(hs[i], train_h).min() <= 4)
        leak[s] = {"images": int(len(idx)), "with_near_duplicate_in_train": int(n), "pct": round(100 * n / max(1, len(idx)), 1)}
    out["leakage_vs_train"] = leak
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / f"results/data_audit/audit_{sys.argv[1]}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
