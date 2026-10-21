"""Generic training experiment runner for the msdd model.

Trains one configuration, then evaluates best.pt on the test split and appends a row to
results/experiments/experiments.csv so configurations can be compared on equal footing.
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path

from ultralytics import RTDETR, YOLO

ROOT = Path(__file__).resolve().parents[1]
DATA = {
    "msdd": ROOT / "data/huggingface/metal-surface-defect-v1/data.yaml",
}
RUNS = ROOT / "해커톤 AI에이전트/runs/exp"
OUT = ROOT / "results/experiments/experiments.csv"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("domain", choices=list(DATA))
    ap.add_argument("model", help="weights or yaml, e.g. yolo11m-seg.pt")
    ap.add_argument("--name", required=True)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--lr0", type=float, default=0.01)
    ap.add_argument("--optimizer", default="auto")
    ap.add_argument("--mosaic", type=float, default=1.0)
    ap.add_argument("--mixup", type=float, default=0.0)
    ap.add_argument("--copy-paste", type=float, default=0.0)
    ap.add_argument("--scale", type=float, default=0.5)
    ap.add_argument("--flipud", type=float, default=0.0)
    ap.add_argument("--degrees", type=float, default=0.0)
    ap.add_argument("--cls", type=float, default=0.5)
    ap.add_argument("--box", type=float, default=7.5)
    ap.add_argument("--patience", type=int, default=40)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--device", default="0")
    ap.add_argument("--data-yaml", default="", help="override the dataset yaml (e.g. data/clean/msdd/data.yaml)")
    a = ap.parse_args()
    data_yaml = Path(a.data_yaml) if a.data_yaml else DATA[a.domain]
    if not data_yaml.is_absolute():
        data_yaml = ROOT / data_yaml

    cls = RTDETR if "rtdetr" in a.model else YOLO
    model = cls(a.model)
    model.train(
        data=str(data_yaml), epochs=a.epochs, imgsz=a.imgsz, batch=a.batch, workers=4,
        device=a.device, project=str(RUNS), name=a.name, exist_ok=True, patience=a.patience,
        lr0=a.lr0, optimizer=a.optimizer, mosaic=a.mosaic, mixup=a.mixup, copy_paste=a.copy_paste,
        scale=a.scale, flipud=a.flipud, degrees=a.degrees, cls=a.cls, box=a.box, seed=a.seed,
        cos_lr=True, close_mosaic=15, plots=False,
    )
    best = RUNS / a.name / "weights/best.pt"
    m = cls(str(best)).val(data=str(data_yaml), split="test", imgsz=a.imgsz, device=a.device,
                           batch=8, verbose=False, plots=False)
    row = {"name": a.name, "domain": a.domain, "model": a.model, "imgsz": a.imgsz, "args": json.dumps(
        {k: v for k, v in vars(a).items() if k not in ("domain", "model", "name", "device")}),
        "box_p": m.box.mp, "box_r": m.box.mr, "box_map50": m.box.map50, "box_map": m.box.map}
    seg = getattr(m, "seg", None)
    if seg is not None and hasattr(seg, "map50"):
        row.update(mask_p=seg.mp, mask_r=seg.mr, mask_map50=seg.map50, mask_map=seg.map)
    new = not OUT.exists()
    with open(OUT, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["name", "domain", "model", "imgsz", "args", "box_p", "box_r", "box_map50",
                                          "box_map", "mask_p", "mask_r", "mask_map50", "mask_map"])
        if new:
            w.writeheader()
        w.writerow(row)
    rec = OUT.parent / a.name                      # keep each run's training curve data next to the summary row
    rec.mkdir(parents=True, exist_ok=True)
    for f in ("results.csv", "args.yaml"):
        if (RUNS / a.name / f).exists():
            shutil.copy2(RUNS / a.name / f, rec / f)
    print("RESULT", json.dumps(row, ensure_ascii=False))


if __name__ == "__main__":
    main()
