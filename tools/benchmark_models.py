"""Evaluate model F1 and inference latency on each domain's test split."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import time
from pathlib import Path

import torch
import yaml
from ultralytics import YOLO


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = {
    "pcb": {
        "weights": ROOT / "해커톤 AI에이전트/models/pcb_v2_yolo11s.pt",
        "data": ROOT / "data/huggingface/pcb-defect-v2/data.yaml",
        "imgsz": 640,
    },
    "msdd": {
        "weights": ROOT / "해커톤 AI에이전트/models/msdd_v1_yolo11s_seg.pt",
        "data": ROOT / "data/huggingface/metal-surface-defect-v1/data.yaml",
        "imgsz": 512,
    },
    "mobile": {
        "weights": ROOT / "해커톤 AI에이전트/models/mobile_surface_yolo11s_seg.pt",
        "data": ROOT / "data/mobile_surface/data.yaml",
        "imgsz": 512,
    },
}


def test_images(data_file: Path) -> list[Path]:
    config = yaml.safe_load(data_file.read_text())
    root = Path(config.get("path", data_file.parent))
    if not root.is_absolute():
        root = (data_file.parent / root).resolve()
    test = Path(config["test"])
    test_dir = test if test.is_absolute() else root / test
    return sorted(
        path
        for path in test_dir.rglob("*")
        if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    )


def sync_cuda() -> None:
    if torch.cuda.is_available():
        torch.cuda.synchronize()


def latency(model: YOLO, images: list[Path], imgsz: int, device: str, warmup: int) -> dict:
    if not images:
        raise RuntimeError("No test images found for latency benchmark")
    warmup_images = images[: min(warmup, len(images))]
    for image in warmup_images:
        model.predict(str(image), imgsz=imgsz, device=device, verbose=False)

    samples = []
    for image in images:
        sync_cuda()
        start = time.perf_counter()
        result = model.predict(str(image), imgsz=imgsz, device=device, verbose=False)[0]
        sync_cuda()
        elapsed_ms = (time.perf_counter() - start) * 1000
        speed = result.speed or {}
        samples.append(
            {
                "wall_ms": elapsed_ms,
                "preprocess_ms": float(speed.get("preprocess", 0.0)),
                "inference_ms": float(speed.get("inference", 0.0)),
                "postprocess_ms": float(speed.get("postprocess", 0.0)),
            }
        )
    wall = [sample["wall_ms"] for sample in samples]
    return {
        "images": len(samples),
        "wall_mean_ms": statistics.mean(wall),
        "wall_p50_ms": statistics.median(wall),
        "wall_p95_ms": sorted(wall)[max(0, int(len(wall) * 0.95) - 1)],
        "model_speed_mean_ms": statistics.mean(
            sample["preprocess_ms"] + sample["inference_ms"] + sample["postprocess_ms"]
            for sample in samples
        ),
        "inference_mean_ms": statistics.mean(sample["inference_ms"] for sample in samples),
    }


def evaluate(name: str, device: str, batch: int, latency_limit: int) -> dict:
    case = DEFAULT_CASES[name]
    weights = Path(case["weights"])
    data = Path(case["data"])
    if not weights.is_file():
        raise FileNotFoundError(weights)
    if not data.is_file():
        raise FileNotFoundError(data)

    model = YOLO(str(weights))
    metrics = model.val(
        data=str(data),
        split="test",
        imgsz=case["imgsz"],
        batch=batch,
        device=device,
        plots=False,
        verbose=False,
    )
    box = metrics.box
    result = {
        "model": name,
        "weights": str(weights),
        "data": str(data),
        "imgsz": case["imgsz"],
        "test_images": len(test_images(data)),
        "box_precision": float(box.mp),
        "box_recall": float(box.mr),
        "box_f1": float(box.f1.mean()),
        "box_map50": float(box.map50),
        "box_map50_95": float(box.map),
    }
    if getattr(metrics, "seg", None) is not None:
        seg = metrics.seg
        result.update(
            {
                "mask_precision": float(seg.mp),
                "mask_recall": float(seg.mr),
                "mask_f1": float(seg.f1.mean()),
                "mask_map50": float(seg.map50),
                "mask_map50_95": float(seg.map),
            }
        )
    images = test_images(data)[:latency_limit]
    result["latency"] = latency(model, images, case["imgsz"], device, warmup=min(10, len(images)))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", default="0")
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--latency-limit", type=int, default=200)
    parser.add_argument("--output", type=Path, default=ROOT / "results/model_benchmark.json")
    parser.add_argument("--models", nargs="+", choices=sorted(DEFAULT_CASES), default=sorted(DEFAULT_CASES))
    args = parser.parse_args()

    results = []
    for name in args.models:
        print(f"[{name}] evaluating", flush=True)
        result = evaluate(name, args.device, args.batch, args.latency_limit)
        results.append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
    csv_path = args.output.with_suffix(".csv")
    fields = [
        "model", "test_images", "box_precision", "box_recall", "box_f1",
        "box_map50", "box_map50_95", "mask_precision", "mask_recall",
        "mask_f1", "mask_map50", "mask_map50_95",
    ]
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)


if __name__ == "__main__":
    main()
