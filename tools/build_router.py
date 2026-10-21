"""Build models/router.joblib: DINOv2 backbone weights + logistic-regression head trained on all domains merged.

Usage: python tools/build_router.py [--backbone vit_small_patch14_dinov2.lvd142m] [--quantile 0.01]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import joblib
import numpy as np
import timm
import torch
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "해커톤 AI에이전트"
sys.path.insert(0, str(APP))
sys.path.insert(0, str(Path(__file__).parent))
from agent.router import embed  # noqa: E402
from router_data import CLASSES, build  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backbone", default="vit_small_patch14_dinov2.lvd142m")
    ap.add_argument("--quantile", type=float, default=0.01, help="fraction of validation images allowed to fall below the reject threshold")
    a = ap.parse_args()
    model = timm.create_model(a.backbone, pretrained=True, num_classes=0, img_size=224).eval()
    mean, std = model.pretrained_cfg["mean"], model.pretrained_cfg["std"]
    ds = build()
    f = {k: embed([p for p, _ in ds[k]], model=model, mean=mean, std=std) for k in ("train", "val", "test", "ood")}
    y = {k: np.array([l for _, l in ds[k]]) for k in ("train", "val", "test")}
    clf = LogisticRegression(max_iter=3000, C=10.0).fit(np.vstack([f["train"], f["val"]]), np.r_[y["train"], y["val"]])
    msp = lambda x: clf.predict_proba(x).max(1)  # noqa: E731
    # threshold from cross-split behaviour: use the training-fit head on val-like data would be optimistic, so fit a separate
    # head on train only for calibration.
    cal = LogisticRegression(max_iter=3000, C=10.0).fit(f["train"], y["train"])
    thr = float(np.quantile(cal.predict_proba(f["val"]).max(1), a.quantile))
    names = np.array([l for _, l in ds["ood"]])
    print(f"threshold {thr:.4f} (val reject {a.quantile:.0%})")
    print("test acc (final head, val included in training only):", float((clf.predict(f["test"]) == y["test"]).mean()))
    print("test accepted:", float((msp(f["test"]) >= thr).mean()), "| OOD accepted:",
          {n: float((msp(f["ood"][names == n]) >= thr).mean()) for n in sorted(set(names))})
    out_w = ROOT / "해커톤 AI에이전트/models/router_backbone.pt"
    torch.save(model.state_dict(), out_w)
    joblib.dump({"backbone": a.backbone, "backbone_weights": "models/router_backbone.pt", "classes": CLASSES, "clf": clf,
                 "threshold": thr}, ROOT / "해커톤 AI에이전트/models/router.joblib")
    print("saved models/router.joblib + router_backbone.pt")


if __name__ == "__main__":
    main()
