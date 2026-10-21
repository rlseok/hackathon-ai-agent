"""Excel result workbooks in the design of 해커톤 AI에이전트/results/confusion_matrix_test.xlsx (one sheet per domain).

  results/confusion_matrix_test.xlsx   confusion matrix per domain (counts, True total / Recall / Missed rate as formulas, "How to read")
  results/model_metrics_test.xlsx      Summary sheet + one sheet per domain: P / R / F1 / AP50 / AP50-95 per class (box, and mask for segmentation)

Both come from running the deployed model on the held-out TEST split (ultralytics val). Counts of the confusion matrix use
detections with confidence >= 0.25 (the agent's "suspected" threshold); P/R/F1/mAP follow the usual ultralytics validation.
Usage: python tools/make_result_workbooks.py [pcb msdd mobile]
"""
from __future__ import annotations

import csv
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))
from benchmark_models import DEFAULT_CASES  # noqa: E402
from make_results import TITLE, VER, split_dir  # noqa: E402

HEAD = PatternFill("solid", fgColor="DCE3EA")
GREEN = PatternFill("solid", fgColor="D9EAD3")
GREY = PatternFill("solid", fgColor="F3F3F3")
ORANGE = PatternFill("solid", fgColor="FCE5CD")
BLUE = Font(color="0000FF")
BOLD = Font(bold=True)
CNT = '#,##0;\\-#,##0;"-"'
PCT = '0.0%;\\-0.0%;"-"'
DEC = '0.000;\\-0.000;"-"'
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT = Alignment(horizontal="left", vertical="center")
SHEET_NAME = {"pcb": "PCB", "msdd": "Metal Surface", "mobile": "Mobile Surface"}
KIND = {"pcb": "defect detection", "msdd": "defect segmentation", "mobile": "defect segmentation"}
NICE = {"pcb": {"falsecopper": "False copper", "missinghole": "Missing hole", "mousebite": "Mouse bite", "opencircuit": "Open circuit",
                "pinhole": "Pin hole", "scratch": "Scratch", "shortcircuit": "Short circuit", "spur": "Spur"}}


def nice(dom, name):
    return NICE.get(dom, {}).get(name, name[:1].upper() + name[1:] if name.islower() else name)


def head(ws, r, c, text, width=None):
    cell = ws.cell(r, c, text)
    cell.font, cell.fill, cell.alignment = BOLD, HEAD, CENTER
    return cell


def title(ws, text, line2):
    ws["A1"] = text
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = line2
    ws["A2"].font = Font(color="555555")
    ws.row_dimensions[1].height = 18.6


def notes(ws, row, lines, source):
    ws.cell(row, 1, "How to read").font = BOLD
    for i, t in enumerate(lines, 1):
        ws.cell(row + i, 1, t)
    ws.cell(row + len(lines) + 1, 1, source).font = Font(italic=True, color="555555")


def test_info(dom):
    case = DEFAULT_CASES[dom]
    img_dir, lab_dir, names = split_dir(case["data"], "test")
    n_img = len([p for p in img_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}])
    n_lab = sum(len([l for l in f.read_text().splitlines() if l.strip()]) for f in lab_dir.glob("*.txt"))
    return case, names, n_img, n_lab


def confusion_sheet(wb, dom, model_name, n_img, n_lab, names, matrix):
    ws = wb.create_sheet(SHEET_NAME[dom])
    nc = len(names)
    title(ws, f"{TITLE[dom]} {KIND[dom]} — confusion matrix (test set)",
          f"Model: {model_name} · Test: {n_img:,} images, {n_lab:,} labeled defects · detections with confidence ≥ 0.25")
    labels = [nice(dom, n) for n in names]
    head(ws, 4, 1, "Predicted \\ True")
    for j, n in enumerate(labels):
        head(ws, 4, 2 + j, n)
    head(ws, 4, 2 + nc, "Background\n(false positive)")
    ws.row_dimensions[4].height = 31.95
    for i in range(nc + 1):                      # predicted classes + "Background (missed)"
        r = 5 + i
        c0 = ws.cell(r, 1, labels[i] if i < nc else "Background (missed)")
        c0.font, c0.alignment = BOLD, LEFT
        c0.fill = HEAD if i < nc else ORANGE
        for j in range(nc + 1):
            if i == nc and j == nc:
                continue
            cell = ws.cell(r, 2 + j, int(matrix[i][j]))
            cell.font, cell.alignment, cell.number_format = BLUE, CENTER, CNT
            if i == j and i < nc:
                cell.fill = GREEN
            elif j == nc:
                cell.fill = GREY
            elif i == nc:
                cell.fill = ORANGE
    r_miss, r_tot = 5 + nc, 6 + nc
    for r, text in ((r_tot, "True total"), (r_tot + 1, "Recall (found as the right type)"), (r_tot + 2, "Missed rate")):
        c = ws.cell(r, 1, text)
        c.font, c.fill, c.alignment = BOLD, HEAD, LEFT
    for j in range(nc):
        col = get_column_letter(2 + j)
        ws.cell(r_tot, 2 + j, f"=SUM({col}5:{col}{r_miss})").number_format = CNT
        ws.cell(r_tot + 1, 2 + j, f"=IF({col}{r_tot}=0,0,{col}{5 + j}/{col}{r_tot})").number_format = PCT
        ws.cell(r_tot + 2, 2 + j, f"=IF({col}{r_tot}=0,0,{col}{r_miss}/{col}{r_tot})").number_format = PCT
        for r in (r_tot, r_tot + 1, r_tot + 2):
            ws.cell(r, 2 + j).alignment = CENTER
    last = get_column_letter(1 + nc)
    diag = "+".join(f"{get_column_letter(2 + j)}{5 + j}" for j in range(nc))
    base = r_tot + 4
    for k, (lab, f, fmt) in enumerate((("All defects (true total)", f"=SUM(B{r_tot}:{last}{r_tot})", CNT),
                                       ("Overall recall", f"=IF(B{base}=0,0,({diag})/B{base})", PCT),
                                       ("Overall missed rate", f"=IF(B{base}=0,0,SUM(B{r_miss}:{last}{r_miss})/B{base})", PCT))):
        c = ws.cell(base + k, 1, lab)
        c.font, c.fill, c.alignment = BOLD, HEAD, LEFT
        v = ws.cell(base + k, 2, f)
        v.number_format, v.alignment = fmt, CENTER
    notes(ws, base + 4, [
        "• Green diagonal = defects found and named correctly. Off-diagonal = found but named as another type.",
        '• Orange row "Background (missed)" = real defects the model did not find.',
        '• Grey column "Background (false positive)" = detections where there is no labeled defect.',
        "• Counts include only detections with confidence ≥ 0.25 (the agent's operating threshold).",
        "• Blue numbers are values produced by the validation run; black cells are formulas.",
    ], f"Source: ultralytics val on the held-out test split, model {model_name}. Rows = predicted class, columns = true class. "
       f"Regenerate with tools/make_result_workbooks.py.")
    ws.column_dimensions["A"].width = 30
    for j in range(nc + 1):
        ws.column_dimensions[get_column_letter(2 + j)].width = 14
    ws.freeze_panes = "B5"


def per_class(m, names, seg=False):
    """-> {class_id: (P, R, AP50, AP50-95)} from an ultralytics metrics object (box or seg)."""
    out = {}
    for k, c in enumerate(m.ap_class_index):
        out[int(c)] = (float(m.p[k]), float(m.r[k]), float(m.ap50[k]), float(m.ap[k]))
    return out


def showcase_rates(dom):
    """class name (lower, no spaces) -> (images_in_case, perfect_rate string) from results/<dom>/showcase/summary.csv."""
    p = ROOT / "results" / dom / "showcase/summary.csv"
    out = {}
    if p.exists():
        for r in csv.DictReader(open(p, encoding="utf-8-sig")):
            key = r["case"].split("_", 1)[1].lower().replace(" ", "")
            out.setdefault(key, (int(r["images_in_case"]), r["perfect_rate"]))
    return out


def metrics_sheet(wb, dom, model_name, n_img, n_lab, names, m, latency):
    ws = wb.create_sheet(SHEET_NAME[dom])
    seg = getattr(m, "seg", None) is not None and hasattr(m.seg, "p") and len(getattr(m.seg, "p", [])) > 0
    title(ws, f"{TITLE[dom]} {KIND[dom]} — performance by class (test set)",
          f"Model: {model_name} · Test: {n_img:,} images, {n_lab:,} labeled defects · IoU 0.5 · P/R at the best-F1 confidence")
    heads = ["Class", "Test labels", "Images with class", "Perfect images"]
    groups = [("Box", per_class(m.box, names))]
    if seg:
        groups.append(("Mask", per_class(m.seg, names)))
    for g, _ in groups:
        heads += [f"{g} P", f"{g} R", f"{g} F1", f"{g} AP50", f"{g} AP50-95"]
    for j, h in enumerate(heads):
        head(ws, 4, 1 + j, h)
    ws.row_dimensions[4].height = 31.95
    rates = showcase_rates(dom)
    nt = m.nt_per_class
    nc = len(names)
    for i in range(nc):
        r = 5 + i
        c = ws.cell(r, 1, nice(dom, names[i]))
        c.font, c.fill, c.alignment = BOLD, HEAD, LEFT
        ws.cell(r, 2, int(nt[i]) if i < len(nt) else 0).number_format = CNT
        imgs, perfect = rates.get(names[i].lower().replace(" ", ""), (None, None))
        ws.cell(r, 3, imgs).number_format = CNT
        ws.cell(r, 4, perfect)
        col = 5
        for _, pc in groups:
            P, R, A50, A = pc.get(i, (0, 0, 0, 0))
            for k, v in enumerate((P, R)):
                ws.cell(r, col + k, round(v, 4)).number_format = DEC
            pl, rl = get_column_letter(col), get_column_letter(col + 1)
            ws.cell(r, col + 2, f"=IF({pl}{r}+{rl}{r}=0,0,2*{pl}{r}*{rl}{r}/({pl}{r}+{rl}{r}))").number_format = DEC
            ws.cell(r, col + 3, round(A50, 4)).number_format = DEC
            ws.cell(r, col + 4, round(A, 4)).number_format = DEC
            col += 5
        for cc in range(2, col):
            cell = ws.cell(r, cc)
            cell.alignment = CENTER
            if cell.value is not None and not (isinstance(cell.value, str) and cell.value.startswith("=")) and cc not in (4,):
                cell.font = BLUE
    r = 5 + nc
    c = ws.cell(r, 1, "All classes")
    c.font, c.fill, c.alignment = BOLD, HEAD, LEFT
    ws.cell(r, 2, f"=SUM(B5:B{r - 1})").number_format = CNT
    ws.cell(r, 3, n_img).number_format = CNT
    col = 5
    for g, _ in groups:
        mm = m.box if g == "Box" else m.seg
        for k, v in enumerate((mm.mp, mm.mr)):
            ws.cell(r, col + k, round(float(v), 4)).number_format = DEC
        fl = get_column_letter(col + 2)
        ws.cell(r, col + 2, f"=AVERAGE({fl}5:{fl}{r - 1})").number_format = DEC      # mean of the per-class F1 (as in model_benchmark.csv)
        ws.cell(r, col + 3, round(float(mm.map50), 4)).number_format = DEC
        ws.cell(r, col + 4, round(float(mm.map), 4)).number_format = DEC
        col += 5
    for cc in range(2, col):
        cell = ws.cell(r, cc)
        cell.alignment, cell.fill = CENTER, GREEN
        if not (isinstance(cell.value, str) and str(cell.value).startswith("=")):
            cell.font = Font(color="0000FF", bold=True)
        else:
            cell.font = BOLD
    ws.cell(r + 2, 1, "Latency (wall clock, per image)").font = BOLD
    ws.cell(r + 2, 2, round(latency["wall_mean_ms"], 1)).number_format = '0.0" ms"'
    ws.cell(r + 3, 1, "Model inference only").font = BOLD
    ws.cell(r + 3, 2, round(latency["inference_mean_ms"], 1)).number_format = '0.0" ms"'
    notes(ws, r + 5, [
        "• P / R / F1 are read at the confidence that maximises F1 for that class; AP50 uses IoU 0.5, AP50-95 averages IoU 0.5–0.95.",
        '• "Perfect images" = share of test images with this class whose detections match the labels exactly (F1 = 1 at IoU 0.5, confidence ≥ 0.25); see results/<domain>/showcase/summary.csv.',
        "• Class F1 is a formula from P and R; the F1 of the green \"All classes\" row is the mean of the class F1 values (same definition as results/model_benchmark.csv). Blue numbers come from the validation run.",
        "• Box metrics measure where the defect is; mask metrics (segmentation models) also measure the outline of the region.",
    ], f"Source: ultralytics val on the held-out test split, model {model_name}. Regenerate with tools/make_result_workbooks.py.")
    ws.column_dimensions["A"].width = 30
    for j in range(2, len(heads) + 1):
        ws.column_dimensions[get_column_letter(j)].width = 13
    ws.freeze_panes = "B5"
    return {"box": (m.box.mp, m.box.mr, m.box.map50, m.box.map), "mask": (m.seg.mp, m.seg.mr, m.seg.map50, m.seg.map) if seg else None,
            "sheet": SHEET_NAME[dom], "row": 5 + nc}


def summary_sheet(wb, rows):
    ws = wb.create_sheet("Summary", 0)
    title(ws, "Model performance on the held-out test sets",
          "Detectors used by the agent (YOLO11s). P / R / F1 at the best-F1 confidence; IoU 0.5. Per-class tables are on the other sheets.")
    heads = ["Domain", "Model", "Test images", "Test labels", "Box P", "Box R", "Box F1", "Box mAP50", "Box mAP50-95",
             "Mask P", "Mask R", "Mask F1", "Mask mAP50", "Mask mAP50-95", "Latency (ms/img)"]
    for j, h in enumerate(heads):
        head(ws, 4, 1 + j, h)
    ws.row_dimensions[4].height = 31.95
    for i, (dom, model_name, n_img, n_lab, vals, lat) in enumerate(rows):
        r = 5 + i
        c = ws.cell(r, 1, TITLE[dom])
        c.font, c.fill, c.alignment = BOLD, HEAD, LEFT
        ws.cell(r, 2, model_name)
        ws.cell(r, 3, n_img).number_format = CNT
        ws.cell(r, 4, n_lab).number_format = CNT
        bp, br, b50, b5095 = vals["box"]
        for k, v in enumerate((bp, br)):
            ws.cell(r, 5 + k, round(float(v), 4)).number_format = DEC
        ws.cell(r, 7, f"='{vals['sheet']}'!G{vals['row']}").number_format = DEC
        ws.cell(r, 8, round(float(b50), 4)).number_format = DEC
        ws.cell(r, 9, round(float(b5095), 4)).number_format = DEC
        if vals["mask"]:
            mp, mr, m50, m5095 = vals["mask"]
            for k, v in enumerate((mp, mr)):
                ws.cell(r, 10 + k, round(float(v), 4)).number_format = DEC
            ws.cell(r, 12, f"='{vals['sheet']}'!L{vals['row']}").number_format = DEC
            ws.cell(r, 13, round(float(m50), 4)).number_format = DEC
            ws.cell(r, 14, round(float(m5095), 4)).number_format = DEC
        else:
            for cc in range(10, 15):
                ws.cell(r, cc, "-")
        ws.cell(r, 15, round(lat["wall_mean_ms"], 1)).number_format = "0.0"
        for cc in range(2, 16):
            cell = ws.cell(r, cc)
            cell.alignment = CENTER
            if cell.value is not None and not (isinstance(cell.value, str) and cell.value.startswith("=")) and cc != 2 and cell.value != "-":
                cell.font = BLUE
    notes(ws, 5 + len(rows) + 1, [
        "• Blue numbers come from the validation run; F1 is linked to the per-domain sheet (mean of the per-class F1, as in results/model_benchmark.csv).",
        "• pcb is a detection model (boxes only); msdd and mobile are segmentation models (box and mask metrics).",
        "• The test sets are the datasets' own held-out splits (pcb 980, msdd 150, mobile 122 images). Latency includes image reading.",
    ], "Source: ultralytics val on the held-out test splits; latency from results/model_benchmark.json. Regenerate with tools/make_result_workbooks.py.")
    ws.column_dimensions["A"].width = 18
    ws.column_dimensions["B"].width = 30
    for j in range(3, 16):
        ws.column_dimensions[get_column_letter(j)].width = 13
    ws.freeze_panes = "C5"


def main():
    doms = sys.argv[1:] or list(VER)
    bench = {}
    bp = ROOT / "results/model_benchmark.json"
    if bp.exists():
        d = json.loads(bp.read_text(encoding="utf-8"))
        d = d if isinstance(d, list) else d.get("results", list(d.values()))
        bench = {x["model"]: x for x in d if isinstance(x, dict) and "model" in x}
    cm_wb, mt_wb = openpyxl.Workbook(), openpyxl.Workbook()
    for wb in (cm_wb, mt_wb):
        del wb["Sheet"]
    rows = []
    for dom in doms:
        case, names, n_img, n_lab = test_info(dom)
        model_name = Path(case["weights"]).name
        model = YOLO(str(case["weights"]))
        print(f"[{dom}] validating ...", flush=True)
        m = model.val(data=str(case["data"]), split="test", imgsz=case["imgsz"], batch=8, plots=False, verbose=False)
        # the confusion matrix is only filled when plots=True; the plot files go to a scratch folder
        m2 = model.val(data=str(case["data"]), split="test", imgsz=case["imgsz"], batch=8, conf=0.25, plots=True, verbose=False,
                       project=str(Path(tempfile.gettempdir()) / "val_cm"), name=dom, exist_ok=True)
        lat = bench.get(dom, {}).get("latency", {"wall_mean_ms": 0.0, "inference_mean_ms": 0.0})
        confusion_sheet(cm_wb, dom, model_name, n_img, n_lab, names, m2.confusion_matrix.matrix)
        vals = metrics_sheet(mt_wb, dom, model_name, n_img, n_lab, names, m, lat)
        rows.append((dom, model_name, n_img, n_lab, vals, lat))
        print(f"[{dom}] done", flush=True)
    summary_sheet(mt_wb, rows)
    cm_wb.save(ROOT / "results/confusion_matrix_test.xlsx")
    mt_wb.save(ROOT / "results/model_metrics_test.xlsx")
    print("saved results/confusion_matrix_test.xlsx, results/model_metrics_test.xlsx")


if __name__ == "__main__":
    main()
