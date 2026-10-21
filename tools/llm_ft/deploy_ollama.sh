#!/bin/sh
# merged HF weights -> GGUF (llama.cpp converter) -> Ollama model "qwen3-defect" (q4_K_M, same quantisation as qwen3:8b)
set -e
cd "$(dirname "$0")"
[ -d llama.cpp ] || git clone --depth 1 https://github.com/ggml-org/llama.cpp.git
.venv/bin/python -m pip --version >/dev/null 2>&1 || uv pip install --python .venv/bin/python pip >/dev/null
uv pip install --python .venv/bin/python gguf numpy sentencepiece protobuf >/dev/null
.venv/bin/python llama.cpp/convert_hf_to_gguf.py out/merged --outfile out/qwen3-defect-f16.gguf --outtype f16
# reuse the chat template / stop tokens / parameters of the stock model
ollama show qwen3:8b --modelfile | sed '/^FROM /d' | sed '/^# Modelfile/d' > out/Modelfile.tail
{ echo "FROM $(pwd)/out/qwen3-defect-f16.gguf"; cat out/Modelfile.tail; } > out/Modelfile
ollama create qwen3-defect -f out/Modelfile -q q4_K_M
ollama list | grep qwen3-defect
