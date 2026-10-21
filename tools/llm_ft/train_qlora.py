"""QLoRA fine-tune of Qwen3-8B on the synthetic Vietnamese report data (data/sft/mix/train.jsonl).

Run with this folder's own venv (tools/llm_ft/.venv): the main pipeline venv is pinned to torch 2.5 / transformers 4.46.
Loss is computed on the assistant answer only. Output: tools/llm_ft/out/qwen3-8b-vi-lora (adapter) + merged copy via merge.py.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, Trainer, TrainingArguments

ROOT = Path(__file__).resolve().parents[2]
BASE = "Qwen/Qwen3-8B"


def encode(tok, ex, max_len):
    msgs = ex["messages"]
    prompt = tok.apply_chat_template(msgs[:-1], tokenize=False, add_generation_prompt=True, enable_thinking=False)
    answer = msgs[-1]["content"] + tok.eos_token
    p_ids = tok(prompt, add_special_tokens=False)["input_ids"]
    a_ids = tok(answer, add_special_tokens=False)["input_ids"]
    if len(p_ids) + len(a_ids) > max_len:        # never cut an answer in half: drop the sample instead
        return None
    return {"input_ids": p_ids + a_ids, "labels": [-100] * len(p_ids) + a_ids}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data/sft/mix/train.jsonl"))
    ap.add_argument("--out", default=str(Path(__file__).parent / "out/qwen3-8b-vi-lora"))
    ap.add_argument("--epochs", type=float, default=2)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--max-len", type=int, default=2560)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    tok = AutoTokenizer.from_pretrained(BASE)
    rows = [json.loads(l) for l in open(a.data, encoding="utf-8")]
    if a.limit:
        rows = rows[:a.limit]
    enc = [e for e in (encode(tok, r, a.max_len) for r in rows) if e]
    ds = Dataset.from_list(enc)
    print("samples", len(ds), "of", len(rows), "(dropped as too long:", len(rows) - len(ds), ") max tokens", max(len(x) for x in ds["input_ids"]))

    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16,
                             bnb_4bit_use_double_quant=True)
    model = AutoModelForCausalLM.from_pretrained(BASE, quantization_config=bnb, torch_dtype=torch.bfloat16, device_map={"": 0})
    # not prepare_model_for_kbit_training(): it upcasts embed_tokens and lm_head (152k vocab) to fp32, ~2.4 GB more VRAM
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.enable_input_require_grads()
    model.config.use_cache = False
    model = get_peft_model(model, LoraConfig(r=a.rank, lora_alpha=2 * a.rank, lora_dropout=0.05, task_type="CAUSAL_LM",
                                             target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]))
    model.print_trainable_parameters()

    def collate(batch):
        m = max(len(b["input_ids"]) for b in batch)
        pad = tok.pad_token_id
        return {"input_ids": torch.tensor([b["input_ids"] + [pad] * (m - len(b["input_ids"])) for b in batch]),
                "attention_mask": torch.tensor([[1] * len(b["input_ids"]) + [0] * (m - len(b["input_ids"])) for b in batch]),
                "labels": torch.tensor([b["labels"] + [-100] * (m - len(b["labels"])) for b in batch])}

    args = TrainingArguments(output_dir=a.out, num_train_epochs=a.epochs, per_device_train_batch_size=1, gradient_accumulation_steps=16,
                             learning_rate=a.lr, lr_scheduler_type="cosine", warmup_ratio=0.05, logging_steps=5, save_strategy="no",
                             bf16=True, optim="paged_adamw_8bit", gradient_checkpointing=True, report_to=[], remove_unused_columns=False)
    class AnswerOnlyTrainer(Trainer):
        """Loss only on the answer tokens: the lm_head (152k vocab) is applied to those positions instead of the whole
        ~1.6k-token sequence, which is what ran out of VRAM on a 12 GB card."""

        def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
            labels = inputs.pop("labels")
            inner = model.base_model.model                      # Qwen3ForCausalLM inside the PEFT wrapper
            hidden = inner.model(input_ids=inputs["input_ids"], attention_mask=inputs["attention_mask"], use_cache=False).last_hidden_state
            target = labels[:, 1:]
            keep = target != -100
            logits = inner.lm_head(hidden[:, :-1][keep]).float()
            return torch.nn.functional.cross_entropy(logits, target[keep])

    AnswerOnlyTrainer(model=model, args=args, train_dataset=ds, data_collator=collate).train()
    model.save_pretrained(a.out)
    tok.save_pretrained(a.out)
    print("saved adapter to", a.out)


if __name__ == "__main__":
    main()
