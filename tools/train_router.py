"""Fine-tune ResNet50 (ImageNet) as the router classifier, then evaluate on test / OOD / perturbations (same protocol as router_probe.py)."""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torchvision
from PIL import Image
from sklearn.metrics import confusion_matrix, f1_score, roc_auc_score
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms as T

sys.path.insert(0, str(Path(__file__).parent))
from router_data import CLASSES, ROOT, build  # noqa: E402
from router_probe import perturb  # noqa: E402

MEAN, STD = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]
OUT = ROOT / "results/router"
EPOCHS = 6


class DS(Dataset):
    def __init__(self, items, tf, kind=None):
        self.items, self.tf, self.kind = items, tf, kind

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        p, y = self.items[i]
        im = Image.open(p).convert("RGB")
        if self.kind:
            im = perturb(im, self.kind)
        return self.tf(im), (y if isinstance(y, int) else -1)


@torch.no_grad()
def logits(model, items, kind=None):
    tf = T.Compose([T.Resize((224, 224)), T.ToTensor(), T.Normalize(MEAN, STD)])
    out = []
    for x, _ in DataLoader(DS(items, tf, kind), batch_size=32, num_workers=4):
        with torch.autocast("cuda", dtype=torch.float16):
            out.append(model(x.cuda()).float().cpu())
    return torch.cat(out)


def main():
    random.seed(0); torch.manual_seed(0)
    ds = build()
    aug = T.Compose([T.RandomResizedCrop(224, scale=(0.4, 1.0)), T.RandomHorizontalFlip(), T.ColorJitter(0.3, 0.3, 0.3, 0.05),
                     T.RandomApply([T.GaussianBlur(5)], p=0.2), T.ToTensor(), T.Normalize(MEAN, STD)])
    model = torchvision.models.resnet50(weights=torchvision.models.ResNet50_Weights.IMAGENET1K_V2)
    model.fc = nn.Linear(2048, len(CLASSES))
    model = model.cuda().to(memory_format=torch.channels_last)
    loader = DataLoader(DS(ds["train"], aug), batch_size=24, shuffle=True, num_workers=4, drop_last=True)
    opt = torch.optim.AdamW(model.parameters(), lr=2e-4, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=2e-4, total_steps=EPOCHS * len(loader))
    scaler = torch.cuda.amp.GradScaler()
    for ep in range(EPOCHS):
        model.train()
        tot = 0
        for x, y in loader:
            with torch.autocast("cuda", dtype=torch.float16):
                loss = nn.functional.cross_entropy(model(x.cuda().contiguous(memory_format=torch.channels_last)), y.cuda(), label_smoothing=0.05)
            opt.zero_grad(set_to_none=True)
            scaler.scale(loss).backward(); scaler.step(opt); scaler.update(); sched.step()
            tot += loss.item()
        model.eval()
        val = logits(model, ds["val"])
        acc = float((val.argmax(1) == torch.tensor([l for _, l in ds["val"]])).float().mean())
        print(f"epoch {ep + 1}/{EPOCHS} loss {tot / len(loader):.4f} val acc {acc:.4f}", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), OUT / "router_resnet50.pt")

    res = {"model": "resnet50-finetune"}
    y_test = np.array([l for _, l in ds["test"]])
    lt = logits(model, ds["test"])
    pred = lt.argmax(1).numpy()
    res["test"] = {"acc": float((pred == y_test).mean()), "macro_f1": float(f1_score(y_test, pred, average="macro")),
                   "confusion": confusion_matrix(y_test, pred).tolist()}
    msp = lambda lg: torch.softmax(lg, 1).max(1).values.numpy()  # noqa: E731
    lo = logits(model, ds["ood"])
    names = np.array([l for _, l in ds["ood"]])
    for n in sorted(set(names)):
        s_in, s_out = msp(lt), msp(lo[torch.tensor(names == n)])
        res[f"auroc_msp_vs_{n}"] = float(roc_auc_score(np.r_[np.ones(len(s_in)), np.zeros(len(s_out))], np.r_[s_in, s_out]))
    thr = float(np.quantile(msp(logits(model, ds["val"])), 0.05))
    res["msp_threshold_val95"] = thr
    res["test_accept_rate"] = float((msp(lt) >= thr).mean())
    res["ood_accept_rate"] = {n: float((msp(lo[torch.tensor(names == n)]) >= thr).mean()) for n in sorted(set(names))}
    sub = ds["test"][::3]
    ys = np.array([l for _, l in sub])
    res["perturb_acc"] = {k: float((logits(model, sub, k).argmax(1).numpy() == ys).mean()) for k in ("jpeg", "blur", "small", "dark", "crop")}
    (OUT / "probe_resnet50-finetune.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
