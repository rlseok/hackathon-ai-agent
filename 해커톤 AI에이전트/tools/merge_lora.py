"""LoRA 어댑터를 원본 가중치에 합친다 — 샤드(safetensors 파일) 하나씩 처리해서 RAM 16GB 노트북에서도 된다.

PEFT LoRA: W' = W + (alpha / r) · B @ A   (A: r×in, B: out×r). 계산은 float32, 저장은 원본 dtype(bf16).
transformers / peft 로 모델 전체를 메모리에 올리지 않는다 (8B bf16 = 16GB 라 RAM 이 모자람).

  python tools/merge_lora.py <원본 폴더> <어댑터 폴더> <출력 폴더>
그 다음: llama.cpp/convert_hf_to_gguf.py <출력 폴더> --outtype f16 → ollama create … -q q4_K_M (docs/06 29절)
"""
import json
import re
import shutil
import sys
from pathlib import Path

import torch
from safetensors import safe_open
from safetensors.torch import save_file


def main(base, adapter, out):
    base, adapter, out = Path(base), Path(adapter), Path(out)
    cfg = json.loads((adapter / 'adapter_config.json').read_text(encoding='utf-8'))
    scale = cfg['lora_alpha'] / cfg['r']
    lora = {}
    with safe_open(adapter / 'adapter_model.safetensors', 'pt') as f:
        for k in f.keys():
            m = re.match(r'base_model\.model\.(.+)\.lora_([AB])\.weight$', k)
            if not m:
                sys.exit(f'unexpected adapter key: {k}')
            lora.setdefault(m.group(1) + '.weight', {})[m.group(2)] = f.get_tensor(k).float()
    print(f'adapter: {len(lora)} target weights, r={cfg["r"]}, alpha={cfg["lora_alpha"]}, scale={scale}')

    out.mkdir(parents=True, exist_ok=True)
    for p in base.iterdir():                       # 설정·토크나이저 등 가중치가 아닌 파일은 그대로
        if p.is_file() and p.suffix != '.safetensors':
            shutil.copy2(p, out / p.name)
    done = set()
    for shard in sorted(base.glob('*.safetensors')):
        tensors = {}
        with safe_open(shard, 'pt') as f:
            meta = f.metadata()
            for k in f.keys():
                t = f.get_tensor(k)
                if k in lora:
                    ab = lora[k]
                    t = (t.float() + scale * (ab['B'] @ ab['A'])).to(t.dtype)
                    done.add(k)
                tensors[k] = t
        save_file(tensors, out / shard.name, metadata=meta or {'format': 'pt'})
        print(f'  {shard.name}: {len(tensors)} tensors')
        del tensors
    missing = set(lora) - done
    if missing:
        sys.exit(f'adapter weights not found in base: {sorted(missing)[:5]} …')
    print(f'merged {len(done)} weights → {out}')


if __name__ == '__main__':
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
