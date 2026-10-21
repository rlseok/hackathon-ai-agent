"""Frozen-feature probes for the router (DINOv2 / CLIP) -> logistic regression, with OOD rejection scores.

Usage: python tools/router_probe.py dinov2-base|dinov2-small|clip-b16 [--perturb]
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import io
import json
import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageFilter
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, f1_score, roc_auc_score

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "해커톤 AI에이전트"))
from agent.device import pick_device  # noqa: E402
from router_data import CLASSES, ROOT, build  # noqa: E402

HF = {"dinov2-small": 0, "dinov2-base": 0, "clip-b16": 0}
MEAN_STD = {"clip": ([0.4815, 0.4578, 0.4082], [0.2686, 0.2613, 0.2758]), "dino": ([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])}


def perturb(img: Image.Image, kind: str) -> Image.Image:
    if kind == "jpeg":
        b = io.BytesIO(); img.save(b, "JPEG", quality=25); b.seek(0); return Image.open(b).convert("RGB")
    if kind == "blur":
        return img.filter(ImageFilter.GaussianBlur(2))
    if kind == "small":
        w, h = img.size; return img.resize((max(32, w // 4), max(32, h // 4))).resize((w, h))
    if kind == "dark":
        return Image.eval(img, lambda v: int(v * 0.5))
    if kind == "crop":
        w, h = img.size; return img.crop((w // 4, h // 4, 3 * w // 4, 3 * h // 4))
    return img


TIMM = {"dinov2-small": "vit_small_patch14_dinov2.lvd142m", "dinov2-base": "vit_base_patch14_dinov2.lvd142m",
        "clip-b16": "vit_base_patch16_clip_224.openai"}


@torch.no_grad()
def extract(name, items, kind=None, bs=32):
    import timm
    dev = pick_device(need_mb=800)         # GPU first, CPU only when another process keeps the GPU busy
    model = timm.create_model(TIMM[name], pretrained=True, num_classes=0, img_size=224).eval()
    model = (model.half() if dev == "cuda" else model).to(dev)        # fp16 only on GPU
    mean, std = model.pretrained_cfg["mean"], model.pretrained_cfg["std"]
    mean, std = torch.tensor(mean, device=dev).view(1, 3, 1, 1), torch.tensor(std, device=dev).view(1, 3, 1, 1)

    def load(p):
        im = Image.open(p).convert("RGB")
        if kind:
            im = perturb(im, kind)
        return np.array(im.resize((224, 224), Image.BICUBIC))

    feats = []
    with ThreadPoolExecutor(8) as pool:        # decode the next batch while the GPU works on this one
        chunks = [[p for p, _ in items[i:i + bs]] for i in range(0, len(items), bs)]
        nxt = pool.submit(lambda c: list(map(load, c)), chunks[0]) if chunks else None
        for k in range(len(chunks)):
            ims = nxt.result()
            nxt = pool.submit(lambda c: list(map(load, c)), chunks[k + 1]) if k + 1 < len(chunks) else None
            x = (torch.from_numpy(np.stack(ims)).permute(0, 3, 1, 2).to(dev).float() / 255 - mean) / std
            feats.append(model(x.half() if dev == "cuda" else x).float().cpu())
    f = torch.cat(feats)
    return torch.nn.functional.normalize(f, dim=1).numpy()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name", choices=list(HF))
    ap.add_argument("--perturb", action="store_true")
    a = ap.parse_args()
    ds = build()
    X = {k: extract(a.name, ds[k]) for k in ("train", "val", "test", "ood")}
    y = {k: np.array([l for _, l in ds[k]]) for k in ("train", "val", "test")}
    clf = LogisticRegression(max_iter=2000, C=10.0).fit(X["train"], y["train"])
    res = {"model": a.name}
    for k in ("val", "test"):
        pred = clf.predict(X[k])
        res[k] = {"acc": float((pred == y[k]).mean()), "macro_f1": float(f1_score(y[k], pred, average="macro")),
                  "confusion": confusion_matrix(y[k], pred).tolist()}
    # OOD rejection: max softmax prob; AUROC of in-distribution (test) vs OOD sets
    msp = lambda x: clf.predict_proba(x).max(1)  # noqa: E731
    ood_names = np.array([l for _, l in ds["ood"]])
    for n in sorted(set(ood_names)):
        s_in, s_out = msp(X["test"]), msp(X["ood"][ood_names == n])
        res[f"auroc_msp_vs_{n}"] = float(roc_auc_score(np.r_[np.ones(len(s_in)), np.zeros(len(s_out))], np.r_[s_in, s_out]))
    # threshold keeping 95% of val in-distribution accepted
    thr = float(np.quantile(msp(X["val"]), 0.05))
    res["msp_threshold_val95"] = thr
    res["test_accept_rate"] = float((msp(X["test"]) >= thr).mean())
    res["ood_accept_rate"] = {n: float((msp(X["ood"][ood_names == n]) >= thr).mean()) for n in sorted(set(ood_names))}
    if a.perturb:
        res["perturb_acc"] = {}
        for kind in ("jpeg", "blur", "small", "dark", "crop"):
            sub = ds["test"][::3]
            res["perturb_acc"][kind] = float((clf.predict(extract(a.name, sub, kind)) == np.array([l for _, l in sub])).mean())
    out = ROOT / "results/router"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"probe_{a.name}.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "val"}, indent=1))


if __name__ == "__main__":
    main()
