#!/usr/bin/env python3
"""Fine-tuning QLoRA untuk SNRB-Vanguard-7B.

Skrip CLI yang mendukung:
  * `--dry-run` : jalankan beberapa step saja (uji pipeline tanpa GPU besar).
  * Training penuh saat GPU tersedia.

Contoh:
    # Uji cepat 3 step
    python src/train_qlora.py --config configs/qlora_default.yaml --dry-run --max-steps 3

    # Training penuh
    python src/train_qlora.py --config configs/qlora_default.yaml \
        --dataset data/samples.jsonl --max-steps -1

Catatan: skrip ini TIDAK dijalankan saat perakitan repo. Semua import berat
(torch/transformers/peft/trl) dilakukan lazy agar `--help` tetap jalan di mesin
tanpa GPU.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_config(path: Path) -> dict:
    import yaml  # lazy: hanya butuh pyyaml

    if not path.exists():
        raise FileNotFoundError(f"Config tidak ditemukan: {path}")
    with path.open("r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    if not isinstance(cfg, dict):
        raise ValueError("Config YAML harus berupa mapping di level atas")
    return cfg


def load_dataset(dataset_path: Path, tokenizer, max_seq_length: int):
    from datasets import load_dataset as hf_load_dataset

    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset tidak ditemukan: {dataset_path}")

    ds = hf_load_dataset("json", data_files=str(dataset_path), split="train")

    def _format(example):
        messages = example["messages"]
        if getattr(tokenizer, "chat_template", None):
            text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=False
            )
        else:
            # Fallback sederhana bila model tanpa chat template
            text = "\n".join(
                f"<|{m['role']}|>\n{m['content']}" for m in messages
            )
        encoded = tokenizer(
            text,
            truncation=True,
            max_length=max_seq_length,
            padding=False,
        )
        encoded["labels"] = list(encoded["input_ids"])
        return encoded

    return ds.map(_format, remove_columns=ds.column_names)


def build_model_and_tokenizer(cfg: dict):
    import torch
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
    )
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

    model_cfg = cfg["model"]
    lora_cfg = cfg["lora"]

    compute_dtype = getattr(torch, model_cfg.get("bnb_4bit_compute_dtype", "bfloat16"))

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=model_cfg.get("load_in_4bit", True),
        bnb_4bit_quant_type=model_cfg.get("bnb_4bit_quant_type", "nf4"),
        bnb_4bit_compute_dtype=compute_dtype,
        bnb_4bit_use_double_quant=model_cfg.get("bnb_4bit_use_double_quant", True),
    )

    tokenizer = AutoTokenizer.from_pretrained(
        model_cfg["base_model"], trust_remote_code=model_cfg.get("trust_remote_code", True)
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_cfg["base_model"],
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=model_cfg.get("trust_remote_code", True),
        attn_implementation=model_cfg.get("attn_implementation", "sdpa"),
    )
    model = prepare_model_for_kbit_training(model)
    model.config.use_cache = False

    peft_config = LoraConfig(
        r=lora_cfg.get("r", 16),
        lora_alpha=lora_cfg.get("lora_alpha", 32),
        lora_dropout=lora_cfg.get("lora_dropout", 0.05),
        bias=lora_cfg.get("bias", "none"),
        task_type=lora_cfg.get("task_type", "CAUSAL_LM"),
        target_modules=lora_cfg.get("target_modules"),
    )
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()
    return model, tokenizer


def main() -> int:
    parser = argparse.ArgumentParser(description="QLoRA fine-tuning SNRB-Vanguard-7B")
    parser.add_argument("--config", default="configs/qlora_default.yaml")
    parser.add_argument("--dataset", default=None,
                        help="Override path dataset (default dari config)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Uji pipeline beberapa step saja")
    parser.add_argument("--max-steps", type=int, default=None,
                        help="-1 = training penuh; >0 = batasi jumlah step")
    parser.add_argument("--output-dir", default=None, help="Override output_dir")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    train_cfg = dict(cfg.get("training", {}))
    data_cfg = dict(cfg.get("data", {}))

    dataset_path = Path(args.dataset or data_cfg.get("dataset_path", "data/samples.jsonl"))
    output_dir = args.output_dir or train_cfg.get("output_dir", "outputs/qlora")
    max_seq_length = int(data_cfg.get("max_seq_length", 2048))

    # Tentukan jumlah step
    if args.max_steps is not None:
        max_steps = args.max_steps
    elif args.dry_run:
        max_steps = 3
    else:
        max_steps = -1

    print(f"[INFO] base_model   : {cfg['model']['base_model']}")
    print(f"[INFO] dataset      : {dataset_path}")
    print(f"[INFO] output_dir   : {output_dir}")
    print(f"[INFO] max_steps    : {max_steps} ({'dry-run' if args.dry_run else 'full'})")
    print(f"[INFO] max_seq_len  : {max_seq_length}")

    try:
        import torch
    except ImportError:
        print("[ERROR] torch belum terpasang. Jalankan: pip install -r requirements.txt",
              file=sys.stderr)
        return 2

    if not torch.cuda.is_available():
        print("[WARN] CUDA tidak terdeteksi. Training QLoRA 4-bit butuh GPU NVIDIA.",
              file=sys.stderr)
        print("[WARN] Perakitan repo tetap valid; jalankan lagi saat GPU aktif.",
              file=sys.stderr)
        if not args.dry_run:
            return 3

    from trl import SFTConfig, SFTTrainer

    model, tokenizer = build_model_and_tokenizer(cfg)
    train_ds = load_dataset(dataset_path, tokenizer, max_seq_length)
    print(f"[INFO] jumlah sampel: {len(train_ds)}")

    sft_kwargs = dict(
        output_dir=output_dir,
        num_train_epochs=train_cfg.get("num_train_epochs", 3),
        per_device_train_batch_size=train_cfg.get("per_device_train_batch_size", 1),
        gradient_accumulation_steps=train_cfg.get("gradient_accumulation_steps", 16),
        learning_rate=float(train_cfg.get("learning_rate", 2e-4)),
        lr_scheduler_type=train_cfg.get("lr_scheduler_type", "cosine"),
        warmup_ratio=train_cfg.get("warmup_ratio", 0.03),
        weight_decay=train_cfg.get("weight_decay", 0.01),
        max_grad_norm=train_cfg.get("max_grad_norm", 1.0),
        logging_steps=train_cfg.get("logging_steps", 10),
        save_steps=train_cfg.get("save_steps", 100),
        save_total_limit=train_cfg.get("save_total_limit", 3),
        bf16=bool(train_cfg.get("bf16", True)),
        fp16=bool(train_cfg.get("fp16", False)),
        optim=train_cfg.get("optim", "paged_adamw_8bit"),
        gradient_checkpointing=bool(train_cfg.get("gradient_checkpointing", True)),
        group_by_length=bool(train_cfg.get("group_by_length", True)),
        report_to=train_cfg.get("report_to", "none"),
        seed=int(train_cfg.get("seed", 42)),
        max_steps=max_steps,
        dataset_text_field=None,  # sudah ditokenisasi
    )

    # Kompatibilitas antar versi TRL: sebagian versi memakai `max_seq_length`,
    # sebagian `max_length`. Coba yang tersedia.
    try:
        sft_config = SFTConfig(max_seq_length=max_seq_length, **sft_kwargs)
    except TypeError:
        sft_config = SFTConfig(max_length=max_seq_length, **sft_kwargs)

    trainer = SFTTrainer(
        model=model,
        args=sft_config,
        train_dataset=train_ds,
        processing_class=tokenizer,
    )

    trainer.train()

    final_dir = Path(output_dir) / "final_adapter"
    trainer.model.save_pretrained(str(final_dir))
    tokenizer.save_pretrained(str(final_dir))

    meta = {
        "base_model": cfg["model"]["base_model"],
        "max_steps": max_steps,
        "dry_run": args.dry_run,
        "samples": len(train_ds),
        "max_seq_length": max_seq_length,
    }
    (Path(output_dir) / "train_meta.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )

    print(f"[OK] Adapter tersimpan di: {final_dir}")
    print("[NEXT] Export ke GGUF: python src/export_gguf.py --adapter-dir "
          f"{final_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
