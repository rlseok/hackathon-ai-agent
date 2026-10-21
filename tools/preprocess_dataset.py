"""Copy a YOLO dataset and apply an image preprocessing method to every image (labels are copied unchanged).

Usage: python tools/preprocess_dataset.py data/clean/msdd clahe data/clean/msdd_clahe
The same transform (agent/preprocess.py) must be applied at inference time for a model trained on the result.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import cv2
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "해커톤 AI에이전트"))
from agent.preprocess import apply  # noqa: E402


def main():
    src, method, dst = (ROOT / sys.argv[1], sys.argv[2], ROOT / sys.argv[3])
    if dst.exists():
        shutil.rmtree(dst)
    n = 0
    for split in ("train", "val", "test"):
        (dst / split / "images").mkdir(parents=True)
        shutil.copytree(src / split / "labels", dst / split / "labels")
        for p in sorted((src / split / "images").iterdir()):
            img = cv2.imread(str(p))
            cv2.imwrite(str(dst / split / "images" / p.name), apply(method, img), [cv2.IMWRITE_JPEG_QUALITY, 97])
            n += 1
    cfg = yaml.safe_load((src / "data.yaml").read_text())
    cfg["path"] = str(dst)
    (dst / "data.yaml").write_text(yaml.safe_dump(cfg, allow_unicode=True))
    print(f"{n} images -> {dst}")


if __name__ == "__main__":
    main()
