"""Build a de-duplicated, leakage-free copy of a YOLO dataset under data/clean/<name>/.

Twins are found with DINOv2 features (cosine >= 0.97; the router backbone features cached in results/router/big_features.npz).
  train : one image per twin group (the one with the most labelled objects); degenerate / duplicate labels removed
  val   : only images with no twin in (original) train, and unique inside val
  test  : only ORIGINAL test images with no twin in original train or val, unique inside test  (= an honest, harder test)
The original split files are never modified. A report with the counts is written to results/data_audit/clean_<name>.json.

Usage: python tools/clean_dataset.py msdd
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT / "해커톤 AI에이전트"))
from router_eval_big import gather  # noqa: E402

CFG = {
    "msdd": {"cls": 1, "root": ROOT / "data/huggingface/metal-surface-defect-v1", "names": ["Dark Spot", "Fold", "Oxidation", "Porosity", "Scratch", "Stain"],
             "dirs": {"train": ("images/train", "labels/train"), "val": ("images/val", "labels/val"), "test": ("images/test", "labels/test")}},
}
TWIN = 0.97


def clean_lines(path: Path) -> list[str]:
    """Keep well-formed labels; drop exact duplicates and boxes thinner than 1% of the image."""
    out, seen = [], set()
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        p = line.split()
        try:
            c, v = int(p[0]), [float(x) for x in p[1:]]
        except (ValueError, IndexError):
            continue
        if not (len(v) == 4 or (len(v) >= 6 and len(v) % 2 == 0)):
            continue
        if len(v) == 4:
            w, h = v[2], v[3]
        else:
            w, h = max(v[0::2]) - min(v[0::2]), max(v[1::2]) - min(v[1::2])
        if w < 0.01 or h < 0.01 or min(v) < -1e-6 or max(v) > 1 + 1e-6:
            continue
        key = (c, tuple(round(x, 4) for x in v))
        if key in seen:
            continue
        seen.add(key)
        out.append(line.strip())
    return out


def main():
    name = sys.argv[1]
    cfg = CFG[name]
    items, _ = gather()
    X = np.load(ROOT / "results/router/big_features.npz")["X"]
    idx = [i for i, it in enumerate(items) if it[1] == cfg["cls"]]
    paths = [Path(items[i][0]) for i in idx]
    split = np.array([items[i][3] for i in idx])
    F = X[idx]
    n_lab = np.array([len(clean_lines(cfg["root"] / cfg["dirs"][s][1] / f"{p.stem}.txt")) for p, s in zip(paths, split)])
    sim = F @ F.T
    np.fill_diagonal(sim, 0)

    train_i = np.where(split == "train")[0]
    keep = {"train": [], "val": [], "test": []}
    taken = []
    # train: collapse twin groups greedily, preferring images with more labels
    for i in sorted(train_i, key=lambda k: -n_lab[k]):
        if not taken or sim[i, taken].max() < TWIN:
            taken.append(i)
    keep["train"] = sorted(taken)
    for s, ref in (("val", train_i), ("test", np.where(split != "test")[0])):
        chosen = []
        for i in np.where(split == s)[0]:
            if sim[i, ref].max() >= TWIN:
                continue
            if chosen and sim[i, chosen].max() >= TWIN:
                continue
            chosen.append(i)
        keep[s] = sorted(chosen)

    out_root = ROOT / "data/clean" / name
    if out_root.exists():
        shutil.rmtree(out_root)
    report = {"dataset": name, "twin_cosine": TWIN, "original": {s: int((split == s).sum()) for s in keep},
              "kept": {s: len(v) for s, v in keep.items()}, "boxes_kept": {}}
    for s, ids in keep.items():
        (out_root / s / "images").mkdir(parents=True)
        (out_root / s / "labels").mkdir(parents=True)
        nb = 0
        for i in ids:
            p = paths[i]
            shutil.copy2(p, out_root / s / "images" / p.name)
            lines = clean_lines(cfg["root"] / cfg["dirs"][split[i]][1] / f"{p.stem}.txt")
            (out_root / s / "labels" / f"{p.stem}.txt").write_text("\n".join(lines) + ("\n" if lines else ""))
            nb += len(lines)
        report["boxes_kept"][s] = nb
    (out_root / "data.yaml").write_text(yaml.safe_dump({
        "path": str(out_root), "train": "train/images", "val": "val/images", "test": "test/images",
        "nc": len(cfg["names"]), "names": cfg["names"]}, allow_unicode=True))
    (ROOT / f"results/data_audit/clean_{name}.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
