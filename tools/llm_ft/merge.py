"""Merge the LoRA adapter into the bf16 base weights (on CPU, so it does not compete for GPU memory)."""
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

HERE = Path(__file__).parent
adapter = HERE / "out/qwen3-8b-vi-lora"
out = HERE / "out/merged"
model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen3-8B", torch_dtype=torch.bfloat16, device_map={"": "cpu"})
model = PeftModel.from_pretrained(model, adapter).merge_and_unload()
model.save_pretrained(out, safe_serialization=True)
AutoTokenizer.from_pretrained("Qwen/Qwen3-8B").save_pretrained(out)
print("merged ->", out)
