#!/bin/bash
# PM2 job "hack-vision-queue": controlled data-preprocessing experiments for the msdd detector (single GPU, one after another).
# Same model + same recipe, only the data differ:  clean (de-duplicated, leakage-free) vs clean + CLAHE.
# Every run is scored on the CLEAN test split of its own dataset and appends a row to results/experiments/experiments.csv.
cd /mnt/hdd/ECG/hackathon-ai-agent || exit 1
W=tools/pretrained
L=results/logs
mkdir -p "$L"
P=.venv/bin/python

# msdd (512px as deployed): 11s-seg, raw vs CLAHE
$P tools/train_exp.py msdd $W/yolo11s-seg.pt --data-yaml data/clean/msdd/data.yaml --name msdd_c_s_raw --imgsz 512 --epochs 80 --batch 16 --patience 30 --copy-paste 0.3 > $L/msdd_c_s_raw.log 2>&1
$P tools/train_exp.py msdd $W/yolo11s-seg.pt --data-yaml data/clean/msdd_clahe/data.yaml --name msdd_c_s_clahe --imgsz 512 --epochs 80 --batch 16 --patience 30 --copy-paste 0.3 > $L/msdd_c_s_clahe.log 2>&1

touch results/logs/.vision_queue.done
