"""Prepare the Kaggle mobile-phone defect masks for YOLO11 segmentation.

The archive contains class folders with JPG images and paired indexed PNG masks:
ground_truth_1 contains Scratch and Stain masks; ground_truth_2 contains Oil masks.
Good images are retained as empty-label normal samples.
"""
from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path

from PIL import Image
import yaml


CLASSES = {"Oil": 0, "Scratch": 1, "Stain": 2}
IMAGE_DIRS = {"Oil": "oil", "Scratch": "scratch", "Stain": "stain"}
MASK_DIRS = {"Oil": "ground_truth_2", "Scratch": "ground_truth_1", "Stain": "ground_truth_1"}


def mask_to_segments(mask: Image.Image) -> list[str]:
    pixels = mask.convert("L")
    width, height = pixels.size
    binary = pixels.point(lambda value: 255 if value else 0)
    import cv2
    import numpy as np

    contours, _ = cv2.findContours(np.asarray(binary), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    segments = []
    for contour in contours:
        if cv2.contourArea(contour) < 2 or len(contour) < 3:
            continue
        points = contour.reshape(-1, 2)
        values = []
        for x, y in points:
            values.extend((f"{x / width:.6f}", f"{y / height:.6f}"))
        if len(values) >= 6:
            segments.append(" ".join(values))
    return segments


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    source, destination = args.source.resolve(), args.destination.resolve()
    if destination.exists():
        raise SystemExit(f"Destination already exists: {destination}")

    items: list[tuple[Path, Path | None, int]] = []
    for class_name, image_dir in IMAGE_DIRS.items():
        mask_dir = source / MASK_DIRS[class_name]
        for image in sorted((source / image_dir).glob("*.jpg")):
            mask = mask_dir / f"{image.stem}.png"
            if not mask.exists():
                raise FileNotFoundError(mask)
            items.append((image, mask, CLASSES[class_name]))
    for image in sorted((source / "good").glob("*.png")):
        items.append((image, None, -1))

    rng = random.Random(args.seed)
    rng.shuffle(items)
    n = len(items)
    cuts = {"train": round(n * 0.8), "val": round(n * 0.9)}
    for split in ("train", "val", "test"):
        (destination / "images" / split).mkdir(parents=True)
        (destination / "labels" / split).mkdir(parents=True)

    for index, (image, mask, class_id) in enumerate(items):
        split = "train" if index < cuts["train"] else "val" if index < cuts["val"] else "test"
        stem = f"{index:05d}_{image.stem}"
        target_image = destination / "images" / split / f"{stem}{image.suffix.lower()}"
        shutil.copy2(image, target_image)
        label_lines = []
        if mask is not None:
            for segment in mask_to_segments(Image.open(mask)):
                label_lines.append(f"{class_id} {segment}")
        (destination / "labels" / split / f"{stem}.txt").write_text(
            "\n".join(label_lines) + ("\n" if label_lines else ""), encoding="utf-8"
        )

    (destination / "data.yaml").write_text(
        yaml.safe_dump({
            "path": str(destination),
            "train": "images/train",
            "val": "images/val",
            "test": "images/test",
            "nc": len(CLASSES),
            "names": ["oil", "scratch", "stain"],
        }, sort_keys=False),
        encoding="utf-8",
    )
    print(f"Prepared {len(items)} images at {destination}")


if __name__ == "__main__":
    main()
