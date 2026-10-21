"""Router evaluation on (almost) all data: (A) images the deployed head never saw, (B) 5-fold group-aware cross-validation over every image.

Groups keep augmentation variants / views of one source together (pcb: base image name, msdd: part), so no near-duplicate leaks across folds.
Usage: python tools/router_eval_big.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "해커톤 AI에이전트"))
sys.path.insert(0, str(Path(__file__).parent))
from agent.router import embed  # noqa: E402
from router_data import CLASSES, OOD, SOURCES, build, files  # noqa: E402

CACHE = ROOT / "results/router/big_features.npz"


def group_of(domain: str, p: Path) -> str:
    n = p.name
    if domain == "pcb":
        return "pcb:" + n.split("_jpg.rf.")[0].split("_png.rf.")[0]
    if domain == "msdd":
        return "msdd:" + n.split("_CAM")[0]
    return "mobile:" + p.stem


def gather():
    items = []
    for ci, c in enumerate(CLASSES):
        base, sub = SOURCES[c]
        for split, rel in sub.items():
            for p in files(base / rel):
                items.append((str(p), ci, group_of(c, p), split))
    ood = [(str(p), name) for name, folder in OOD.items() for p in files(folder)]
    return items, ood


def features():
    items, ood = gather()
    if CACHE.exists():
        z = np.load(CACHE, allow_pickle=True)
        if len(z["X"]) == len(items) and len(z["O"]) == len(ood):
            return items, ood, z["X"], z["O"]
    X = embed([p for p, *_ in items])
    O = embed([p for p, _ in ood])
    np.savez(CACHE, X=X, O=O)
    return items, ood, X, O


def report(y, pred, accepted, ood_acc=None):
    y, pred, accepted = map(np.asarray, (y, pred, accepted))
    r = {"n": int(len(y)), "uncertain_rate": float(1 - accepted.mean()),
         "acc_overall": float(((pred == y) & accepted).mean()),                # uncertain counts as not-auto-correct
         "acc_when_accepted": float((pred[accepted] == y[accepted]).mean()),
         "wrong_accepted": int(((pred != y) & accepted).sum()),
         "per_class": {}}
    for ci, c in enumerate(CLASSES):
        m = y == ci
        if m.any():
            r["per_class"][c] = {"n": int(m.sum()), "recall_auto": float(((pred == y) & accepted)[m].mean()),
                                 "wrong_accepted": int(((pred != y) & accepted)[m].sum())}
    if ood_acc is not None:
        r["ood_accepted_rate"] = ood_acc
    return r


def main():
    items, ood, X, O = features()
    y = np.array([c for _, c, _, _ in items])
    groups = np.array([g for _, _, g, _ in items])
    ood_names = np.array([n for _, n in ood])
    print("images", len(items), dict(Counter(CLASSES[c] for c in y)), "| OOD", dict(Counter(ood_names)))

    # (A) the deployed head: evaluate only on images that were not in its training data (train+val of build())
    art = joblib.load(ROOT / "해커톤 AI에이전트/models/router.joblib")
    ds = build()
    used = {p for p, _ in ds["train"]} | {p for p, _ in ds["val"]}
    unseen = np.array([p not in used for p, *_ in items])
    pr = art["clf"].predict_proba(X)
    pred, conf = pr.argmax(1), pr.max(1)
    acc_mask = conf >= art["threshold"]
    po = art["clf"].predict_proba(O).max(1) >= art["threshold"]
    A = report(y[unseen], pred[unseen], acc_mask[unseen],
               {n: float(po[ood_names == n].mean()) for n in sorted(set(ood_names))})
    A["note"] = "images never used to train/calibrate the deployed head (original test split + unused pcb train images)"
    print("\n(A) deployed head on unseen images:", json.dumps(A, ensure_ascii=False, indent=1))

    # (B) 5-fold group CV over everything (class-balanced head; threshold = 3% quantile of an inner validation split)
    preds, accepted = np.zeros(len(y), int), np.zeros(len(y), bool)
    ood_acc = {n: [] for n in sorted(set(ood_names))}
    for k, (tr, te) in enumerate(GroupKFold(n_splits=5).split(X, y, groups)):
        gtr = np.unique(groups[tr])
        rng = np.random.RandomState(k)
        inner_val = set(rng.choice(gtr, size=max(1, len(gtr) // 10), replace=False))
        iv = np.array([g in inner_val for g in groups[tr]])
        cal = LogisticRegression(max_iter=3000, C=10.0, class_weight="balanced").fit(X[tr][~iv], y[tr][~iv])
        thr = float(np.quantile(cal.predict_proba(X[tr][iv]).max(1), 0.03))
        clf = LogisticRegression(max_iter=3000, C=10.0, class_weight="balanced").fit(X[tr], y[tr])
        p = clf.predict_proba(X[te])
        preds[te], accepted[te] = p.argmax(1), p.max(1) >= thr
        po = clf.predict_proba(O).max(1) >= thr
        for n in ood_acc:
            ood_acc[n].append(float(po[ood_names == n].mean()))
        print(f"fold {k}: n={len(te)} acc_overall={((p.argmax(1) == y[te]) & (p.max(1) >= thr)).mean():.4f}", flush=True)
    B = report(y, preds, accepted, {n: float(np.mean(v)) for n, v in ood_acc.items()})
    B["note"] = "5-fold GroupKFold over all images (14,622)"
    print("\n(B) 5-fold group cross-validation:", json.dumps(B, ensure_ascii=False, indent=1))
    (ROOT / "results/router/big_eval.json").write_text(json.dumps({"A_deployed_unseen": A, "B_group_cv": B}, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
