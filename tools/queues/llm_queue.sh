#!/bin/bash
# PM2 job "hack-llm-queue": fine-tune Qwen3-8B (ko/vi/en + retrieved knowledge) -> merge -> GGUF/Ollama -> evaluate base vs tuned.
# Starts only after hack-vision-queue has finished (same GPU).
cd /mnt/hdd/ECG/hackathon-ai-agent || exit 1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
L=results/logs
mkdir -p "$L"
while [ ! -f results/logs/.vision_queue.done ]; do sleep 60; done
cd tools/llm_ft || exit 1
.venv/bin/python train_qlora.py --epochs 2 > ../../$L/llm_train.log 2>&1 || exit 1
CUDA_VISIBLE_DEVICES= .venv/bin/python merge.py > ../../$L/llm_merge.log 2>&1 || exit 1
./deploy_ollama.sh > ../../$L/llm_deploy.log 2>&1 || exit 1
cd ../..
.venv/bin/python tools/llm_ft/eval_llm.py qwen3:8b --out results/llm/eval_base.json > $L/llm_eval_base.log 2>&1
.venv/bin/python tools/llm_ft/eval_llm.py qwen3-defect --out results/llm/eval_tuned.json > $L/llm_eval_tuned.log 2>&1
