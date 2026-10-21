"""Router dataset: merge every domain's images into one classification set (label = which detector should handle it).

Splits follow each source dataset's own train/val/test (msdd and pcb are already split by part/group, so no part leaks across splits).
OOD ("unknown") sets are images that no detector was trained for; they are used only to calibrate/evaluate rejection.
"""
from __future__ import annotations

import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "data"
CLASSES = ["pcb", "msdd", "mobile"]
IMG = {".jpg", ".jpeg", ".png", ".bmp"}
SOURCES = {
    "pcb": (D / "huggingface/pcb-defect-v2/images", {"train": "train", "val": "val", "test": "test"}),
    "msdd": (D / "huggingface/metal-surface-defect-v1/images", {"train": "train", "val": "val", "test": "test"}),
    "mobile": (D / "mobile_surface/images", {"train": "train", "val": "val", "test": "test"}),
}
OOD = {   # not any detector's domain
    "ood_ui_screens": D / "huggingface/android-screen-defects",
    "ood_synthetic_metal": D / "huggingface/synthetic-industrial-defects-teaser/images",
}
CAP = {"train": 1200, "val": 150}      # per class; test is always complete


def files(folder: Path) -> list[Path]:
    return sorted(p for p in folder.rglob("*") if p.suffix.lower() in IMG)


def build(seed: int = 0) -> dict:
    rng = random.Random(seed)
    out = {"train": [], "val": [], "test": [], "ood": []}
    for ci, c in enumerate(CLASSES):
        base, sub = SOURCES[c]
        for split, rel in sub.items():
            fs = files(base / rel)
            if split in CAP and len(fs) > CAP[split]:
                fs = rng.sample(fs, CAP[split])
            out[split] += [(str(p), ci) for p in fs]
    for name, folder in OOD.items():
        fs = files(folder)
        out["ood"] += [(str(p), name) for p in rng.sample(fs, min(len(fs), 300))]
    return out


if __name__ == "__main__":
    ds = build()
    for k, v in ds.items():
        print(k, len(v), {c: sum(1 for _, l in v if l == i) for i, c in enumerate(CLASSES)} if k != "ood" else "")
