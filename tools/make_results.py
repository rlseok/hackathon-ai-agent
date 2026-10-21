"""Build results/<domain>/ for every detector in the same layout as 해커톤 AI에이전트/results (pcb, msdd) so all four domains are comparable.

  results/<domain>/test_eval_<ver>/   confusion matrices, PR/F1/P/R curves, val_batch0 labels/pred   (ultralytics val on the TEST split)
  results/<domain>/showcase/          one folder per defect class: best test images, ground truth (left) vs prediction (right),
                                      overview.jpg, originals/{images,labels}, and summary.csv  (case, images_in_case, perfect_images, ...)
  results/<domain>/<split file>       image -> split / group info
  results/confusion_matrix_test.xlsx  one sheet per domain (counts + row-normalised)

Image score = F1 at IoU 0.5 (class-aware, conf >= 0.25) between ground truth and prediction; "perfect" = F1 of 1.
Training records (train_<ver>/) are copied from the existing package results where they exist (pcb, msdd) or from the original run folder.

Usage: python tools/make_results.py [pcb msdd mobile]
"""
from __future__ import annotations

import csv
import shutil
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
import yaml
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "해커톤 AI에이전트"
sys.path.insert(0, str(Path(__file__).parent))
from benchmark_models import DEFAULT_CASES  # noqa: E402

VER = {"pcb": "v2", "msdd": "v1", "mobile": "v1"}
TITLE = {"pcb": "PCB", "msdd": "Metal Surface", "mobile": "Mobile Surface"}
CONF = 0.25
PER_CASE = 6
IMG = {".jpg", ".jpeg", ".png", ".bmp"}
COLORS = [(60, 180, 75), (230, 25, 75), (0, 130, 200), (245, 130, 48), (145, 30, 180), (70, 240, 240), (240, 50, 230), (210, 245, 60)]


def split_dir(yaml_path: Path, key: str) -> tuple[Path, Path, list[str]]:
    cfg = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    root = Path(cfg.get("path", yaml_path.parent))
    if not root.is_absolute():
        root = (yaml_path.parent / root).resolve()
    img = Path(cfg[key])
    img = img if img.is_absolute() else (root / img).resolve()
    lab = Path(str(img).replace("/images", "/labels"))
    names = cfg["names"]
    names = [names[i] for i in sorted(names)] if isinstance(names, dict) else list(names)
    return img, lab, names


def read_gt(label_file: Path, w: int, h: int):
    """-> list of (class, bbox xyxy px, polygon px or None)"""
    out = []
    if not label_file.exists():
        return out
    for line in label_file.read_text().splitlines():
        p = line.split()
        if len(p) < 5:
            continue
        c, v = int(p[0]), [float(x) for x in p[1:]]
        if len(v) == 4:
            cx, cy, bw, bh = v
            out.append((c, [(cx - bw / 2) * w, (cy - bh / 2) * h, (cx + bw / 2) * w, (cy + bh / 2) * h], None))
        else:
            pts = np.array(v).reshape(-1, 2) * [w, h]
            out.append((c, [pts[:, 0].min(), pts[:, 1].min(), pts[:, 0].max(), pts[:, 1].max()], pts))
    return out


def iou(a, b):
    ix, iy = max(0, min(a[2], b[2]) - max(a[0], b[0])), max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    return inter / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter + 1e-9)


def f1_score(gt, pred):
    used, tp = set(), 0
    for pc, pb, _, _ in sorted(pred, key=lambda x: -x[3]):
        best = max(((iou(pb, g[1]), i) for i, g in enumerate(gt) if i not in used and g[0] == pc), default=(0, -1))
        if best[0] >= 0.5:
            used.add(best[1])
            tp += 1
    fp, fn = len(pred) - tp, len(gt) - tp
    return 1.0 if (tp + fp + fn) == 0 else 2 * tp / (2 * tp + fp + fn)


def draw(img, items, names, conf=False):
    out = img.copy()
    th = max(2, round(max(img.shape[:2]) / 400))
    for c, box, poly, *rest in items:
        col = COLORS[c % len(COLORS)]
        if poly is not None:
            ov = out.copy()
            cv2.fillPoly(ov, [poly.astype(np.int32)], col)
            out = cv2.addWeighted(ov, 0.3, out, 0.7, 0)
            cv2.polylines(out, [poly.astype(np.int32)], True, col, th)
        else:
            cv2.rectangle(out, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), col, th)
        label = names[c] + (f" {rest[0]:.2f}" if conf and rest else "")
        cv2.putText(out, label, (int(box[0]), max(14, int(box[1]) - 4)), cv2.FONT_HERSHEY_SIMPLEX, max(0.5, th / 4), col, max(1, th - 1))
    return out


def panel(img, items_gt, items_pred, names, width=640):
    s = width / img.shape[1]
    small = cv2.resize(img, (width, int(img.shape[0] * s)))
    def sc(items):
        out = []
        for c, b, poly, *r in items:
            out.append((c, [x * s for x in b], None if poly is None else poly * s, *r))
        return out
    left, right = draw(small, sc(items_gt), names), draw(small, sc(items_pred), names, conf=True)
    for im, t in ((left, "GT"), (right, "Prediction")):
        cv2.putText(im, t, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 3)
        cv2.putText(im, t, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)
    return np.hstack([left, right])


def predict_items(model, path: Path, imgsz: int):
    r = model.predict(str(path), imgsz=imgsz, conf=CONF, verbose=False)[0]
    out = []
    polys = r.masks.xy if r.masks is not None else [None] * len(r.boxes)
    for b, c, cf, p in zip(r.boxes.xyxy.cpu().numpy(), r.boxes.cls.cpu().numpy(), r.boxes.conf.cpu().numpy(), polys):
        out.append((int(c), b.tolist(), None if p is None or len(p) < 3 else np.asarray(p), float(cf)))
    return out


def build_showcase(model, dom, data_yaml, imgsz, names, out_dir: Path):
    img_dir, lab_dir, _ = split_dir(data_yaml, "test")
    files = sorted(p for p in img_dir.iterdir() if p.suffix.lower() in IMG)
    rows = defaultdict(list)       # case -> [(score, n_gt, path, gt, pred)]
    for p in files:
        im = cv2.imread(str(p))
        h, w = im.shape[:2]
        gt = read_gt(lab_dir / f"{p.stem}.txt", w, h)
        pred = predict_items(model, p, imgsz)
        score = f1_score(gt, [(c, b, po, cf) for c, b, po, cf in pred]) if gt or pred else 1.0
        if not gt:
            rows["Normal"].append((score, 0, p, gt, pred))
        for c in sorted({g[0] for g in gt}):
            rows[names[c]].append((score, len(gt), p, gt, pred))
    shutil.rmtree(out_dir, ignore_errors=True)
    summary = []
    for ci, case in enumerate(sorted(rows, key=lambda k: (k == "Normal", names.index(k) if k in names else 99))):
        items = rows[case]
        perfect = sum(1 for s, *_ in items if s == 1.0)
        ranked = sorted(items, key=lambda t: (-t[0], -t[1]))[:PER_CASE]
        cdir = out_dir / f"{ci:02d}_{case.replace(' ', '')}"
        (cdir / "originals/images").mkdir(parents=True)
        (cdir / "originals/labels").mkdir(parents=True)
        thumbs = []
        for rank, (score, ngt, p, gt, pred) in enumerate(ranked, 1):
            im = cv2.imread(str(p))
            comp = panel(im, gt, pred, names)
            stem = f"{rank:02d}_{p.name}"[:70]
            cv2.imwrite(str(cdir / (stem.rsplit('.', 1)[0] + ".jpg")), comp, [cv2.IMWRITE_JPEG_QUALITY, 82])
            small = cv2.resize(im, (int(im.shape[1] * 420 / im.shape[0]), 420)) if im.shape[0] > 420 else im
            cv2.imwrite(str(cdir / "originals/images" / f"{rank:02d}_{p.name}"), small if max(im.shape[:2]) > 1000 else im)
            lab = lab_dir / f"{p.stem}.txt"
            (cdir / "originals/labels" / f"{rank:02d}_{p.stem}.txt").write_text(lab.read_text() if lab.exists() else "")
            thumbs.append(cv2.resize(comp, (640, int(comp.shape[0] * 640 / comp.shape[1]))))
            summary.append([cdir.name, len(items), perfect, f"{100 * perfect / len(items):.1f}%", rank, p.name, f"{score:.4f}", ngt])
        if thumbs:
            h = max(t.shape[0] for t in thumbs)
            thumbs = [cv2.copyMakeBorder(t, 0, h - t.shape[0], 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255)) for t in thumbs]
            while len(thumbs) % 2:
                thumbs.append(np.full_like(thumbs[0], 255))
            grid = np.vstack([np.hstack(thumbs[i:i + 2]) for i in range(0, len(thumbs), 2)])
            cv2.imwrite(str(cdir / "overview.jpg"), grid, [cv2.IMWRITE_JPEG_QUALITY, 80])
    with open(out_dir / "summary.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["case", "images_in_case", "perfect_images", "perfect_rate", "rank", "image", "score", "n_defects"])
        w.writerows(summary)


def write_split_csv(dom, data_yaml, out: Path):
    rows = []
    for split, key in (("train", "train"), ("val", "val"), ("test", "test")):
        img_dir, lab_dir, names = split_dir(data_yaml, key)
        for p in sorted(img_dir.iterdir()):
            if p.suffix.lower() in IMG:
                lab = lab_dir / f"{p.stem}.txt"
                n = len([l for l in lab.read_text().splitlines() if l.strip()]) if lab.exists() else 0
                rows.append([p.name, split, n])
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["image", "split", "n_defects"])
        w.writerows(rows)


def confusion_sheet(wb, dom, model_name, n_img, n_lab, names, matrix):
    ws = wb.create_sheet(TITLE[dom])
    ws.append([f"{TITLE[dom]} detection — confusion matrix (test set)"])
    ws.append([f"Model: {model_name} · Test: {n_img} images, {n_lab} labeled defects"])
    ws.append([])
    head = ["Predicted \\ True"] + names + ["Background\n(false positive)"]
    ws.append(head)
    labels = names + ["Background\n(missed)"]
    for i, lab in enumerate(labels):
        ws.append([lab] + [int(x) for x in matrix[i]])
    ws.append([])
    ws.append(["Row-normalised (share of each predicted class)"])
    ws.append(head)
    for i, lab in enumerate(labels):
        s = max(1, matrix[i].sum())
        ws.append([lab] + [round(float(x) / s, 3) for x in matrix[i]])
    ws.column_dimensions["A"].width = 22


def main():
    import openpyxl
    doms = sys.argv[1:] or list(VER)
    xlsx = ROOT / "results/confusion_matrix_test.xlsx"
    wb = openpyxl.load_workbook(xlsx) if xlsx.exists() and sys.argv[1:] else openpyxl.Workbook()
    if "Sheet" in wb.sheetnames:
        del wb["Sheet"]
    for dom in doms:
        case = DEFAULT_CASES[dom]
        ver = VER[dom]
        out = ROOT / "results" / dom
        out.mkdir(parents=True, exist_ok=True)
        model = YOLO(str(case["weights"]))
        _, _, names = split_dir(case["data"], "test")
        print(f"[{dom}] test_eval ...", flush=True)
        ev = out / f"test_eval_{ver}"
        shutil.rmtree(ev, ignore_errors=True)
        m = model.val(data=str(case["data"]), split="test", imgsz=case["imgsz"], batch=8, plots=True, project=str(out),
                      name=f"test_eval_{ver}", exist_ok=True, verbose=False)
        for junk in ev.glob("*.json"):
            junk.unlink()
        img_dir, lab_dir, _ = split_dir(case["data"], "test")
        n_img = len([p for p in img_dir.iterdir() if p.suffix.lower() in IMG])
        n_lab = sum(len([l for l in f.read_text().splitlines() if l.strip()]) for f in lab_dir.glob("*.txt"))
        confusion_sheet(wb, dom, Path(case["weights"]).name, n_img, n_lab, names, m.confusion_matrix.matrix)
        print(f"[{dom}] showcase ...", flush=True)
        build_showcase(model, dom, case["data"], case["imgsz"], names, out / "showcase")
        write_split_csv(dom, case["data"], out / "splits.csv")
        print(f"[{dom}] done", flush=True)
    wb.save(xlsx)
    print("saved", xlsx)


if __name__ == "__main__":
    main()
