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
import inspect
import json
import math
import sys
from pathlib import Path

# Argumen konfigurasi yang dihapus/diganti di versi library yang lebih baru.
# Dipakai untuk memetakan nilai lama ke padanan barunya, bukan sekadar dibuang.
_KWARG_ALIASES = {
    # trl <= 0.11 memakai max_seq_length; trl >= 0.12 memakai max_length
    "max_seq_length": ("max_length", "max_seq_length"),
    "max_length": ("max_length", "max_seq_length"),
    # transformers v6 mengganti nama gradient_checkpointing
    "gradient_checkpointing": ("activation_checkpointing", "gradient_checkpointing"),
    "activation_checkpointing": ("activation_checkpointing", "gradient_checkpointing"),
}


def load_config(path: Path) -> dict:
    import yaml  # lazy: hanya butuh pyyaml

    if not path.exists():
        raise FileNotFoundError(f"Config tidak ditemukan: {path}")
    with path.open("r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    if not isinstance(cfg, dict):
        raise ValueError("Config YAML harus berupa mapping di level atas")
    return cfg


def config_init_params(cls) -> set[str]:
    """Nama parameter yang benar-benar diterima `cls.__init__`.

    Mengembalikan set kosong bila signature tidak bisa dibaca (mis. C extension),
    sehingga pemanggil bisa memilih jalur aman.
    """
    try:
        sig = inspect.signature(cls.__init__)
    except (TypeError, ValueError):
        return set()
    return {name for name in sig.parameters if name != "self"}


def resolve_length_kwarg(accepted: set[str]) -> str | None:
    """Nama argumen panjang sequence: `max_length` (trl baru) atau `max_seq_length` (lama)."""
    for candidate in ("max_length", "max_seq_length"):
        if candidate in accepted:
            return candidate
    return None


def filter_supported_kwargs(
    accepted: set[str], desired: dict
) -> tuple[dict, list[tuple[str, str]]]:
    """Saring `desired` agar hanya berisi argumen yang dikenal versi terpasang.

    Nilai untuk argumen yang di-rename dipetakan ke namanya yang baru (mis.
    `max_seq_length` -> `max_length`). Argumen yang benar-benar tidak ada
    dikembalikan sebagai daftar `(key, alasan)` agar bisa dilaporkan, bukan
    hilang diam-diam.
    """
    if not accepted:
        return dict(desired), []

    resolved: dict = {}
    dropped: list[tuple[str, str]] = []
    for key, value in desired.items():
        if key in accepted:
            resolved[key] = value
            continue
        alias = next((a for a in _KWARG_ALIASES.get(key, ()) if a in accepted), None)
        if alias is not None:
            resolved.setdefault(alias, value)
            continue
        dropped.append((key, "tidak dikenal versi terpasang"))
    return resolved, dropped


def resolve_warmup_kwargs(
    train_cfg: dict, resolved: dict, num_samples: int, accepted: set[str]
) -> tuple[dict, list[tuple[str, str]]]:
    """Terjemahkan `warmup_ratio` -> `warmup_steps` bila versi terpasang sudah membuangnya.

    `warmup_ratio` dihapus di transformers>=5, jadi rasionya dihitung manual dari
    jumlah step total (epochs x langkah per epoch, atau `max_steps` bila dibatasi).
    """
    if "warmup_steps" in accepted:
        if "warmup_steps" in train_cfg:
            return {"warmup_steps": int(train_cfg["warmup_steps"])}, []
        ratio = float(train_cfg.get("warmup_ratio", 0.0) or 0.0)
        if ratio <= 0:
            return {"warmup_steps": 0}, []

        max_steps = int(resolved.get("max_steps", -1) or -1)
        if max_steps > 0:
            total_steps = max_steps
        else:
            batch = max(1, int(resolved.get("per_device_train_batch_size", 1)))
            accum = max(1, int(resolved.get("gradient_accumulation_steps", 1)))
            epochs = float(resolved.get("num_train_epochs", 1))
            steps_per_epoch = max(1, math.ceil(num_samples / (batch * accum)))
            total_steps = max(1, int(round(steps_per_epoch * epochs)))
        return {"warmup_steps": max(1, int(round(total_steps * ratio)))}, []

    if "warmup_ratio" in accepted:
        return {"warmup_ratio": float(train_cfg.get("warmup_ratio", 0.03))}, []
    return {}, [("warmup_ratio", "tidak ada padanan warmup di versi terpasang")]


def resolve_precision(torch, train_cfg: dict) -> tuple[dict, list[tuple[str, str]]]:
    """Pilih presisi campuran yang benar-benar didukung GPU.

    T4 (Turing, compute capability 7.5) tidak mendukung bfloat16. Memaksa
    `bf16=True` di sana gagal saat training, jadi turunkan ke fp16 dan laporkan.
    """
    bf16 = bool(train_cfg.get("bf16", False))
    fp16 = bool(train_cfg.get("fp16", False))
    notes: list[tuple[str, str]] = []

    has_cuda = bool(getattr(torch, "cuda", None) and torch.cuda.is_available())
    if not has_cuda:
        if bf16 or fp16:
            notes.append(("bf16/fp16", "CUDA tidak tersedia; presisi campuran dimatikan"))
        return {"bf16": False, "fp16": False}, notes

    if bf16 and fp16:
        notes.append(("fp16", "bf16 dan fp16 aktif bersamaan; fp16 dimatikan"))
        fp16 = False

    if bf16:
        try:
            supported = bool(torch.cuda.is_bf16_supported())
        except Exception:
            supported = False
        if not supported:
            notes.append(("bf16", "GPU tidak mendukung bfloat16 (mis. T4); beralih ke fp16"))
            bf16, fp16 = False, True

    return {"bf16": bf16, "fp16": fp16}, notes


def build_sft_config(SFTConfig, desired: dict, max_seq_length: int):
    """Bangun `SFTConfig` tanpa `TypeError`, apa pun versi trl-nya.

    Mengembalikan `(config, dropped)` di mana `dropped` berisi argumen yang tidak
    dikenal versi terpasang (agar bisa dilaporkan ke pengguna).
    """
    accepted = config_init_params(SFTConfig)

    payload = dict(desired)
    length_name = resolve_length_kwarg(accepted)
    if length_name:
        payload[length_name] = max_seq_length
    elif accepted:
        print(
            "[WARN] SFTConfig tidak punya max_length/max_seq_length; "
            "panjang sequence mengikuti default library.",
            file=sys.stderr,
        )

    resolved, dropped = filter_supported_kwargs(accepted, payload)
    return SFTConfig(**resolved), dropped


def sort_by_length(dataset):
    """Urutkan dataset ter-tokenisasi per panjang agar padding per batch minimal.

    Pengganti `group_by_length` yang dihapus di transformers>=5.
    """
    try:
        return dataset.sort("length")
    except Exception:
        return dataset


def build_trainer_kwargs(SFTTrainer, model, sft_config, train_ds, tokenizer) -> dict:
    """Susun kwargs `SFTTrainer` sesuai nama parameter versi terpasang.

    trl lama memakai `tokenizer=`, trl baru memakai `processing_class=`.
    """
    accepted = config_init_params(SFTTrainer)
    kwargs = {"model": model, "args": sft_config, "train_dataset": train_ds}
    if not accepted or "processing_class" in accepted:
        kwargs["processing_class"] = tokenizer
    elif "tokenizer" in accepted:
        kwargs["tokenizer"] = tokenizer
    return kwargs


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
        # Kolom `length` dipakai untuk mengurutkan per panjang (pengganti group_by_length).
        encoded["length"] = len(encoded["input_ids"])
        return encoded

    return ds.map(_format, remove_columns=ds.column_names)


def resolve_compute_dtype(torch, name: str):
    """Pilih dtype komputasi 4-bit yang didukung GPU terpasang.

    `bfloat16` tidak didukung T4; bitsandbytes akan gagal saat forward pass.
    Turunkan ke `float16` dan laporkan, bukan crash.
    """
    dtype_name = str(name or "bfloat16").lower()
    dtype = getattr(torch, dtype_name, torch.float16)

    if dtype is torch.bfloat16:
        has_cuda = bool(getattr(torch, "cuda", None) and torch.cuda.is_available())
        supported = False
        if has_cuda:
            try:
                supported = bool(torch.cuda.is_bf16_supported())
            except Exception:
                supported = False
        if not supported:
            print(
                "[WARN] bnb_4bit_compute_dtype=bfloat16 tidak didukung GPU ini; "
                "memakai float16.",
                file=sys.stderr,
            )
            return torch.float16
    return dtype


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

    compute_dtype = resolve_compute_dtype(torch, model_cfg.get("bnb_4bit_compute_dtype", "bfloat16"))

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


def build_training_args(
    SFTConfig, train_cfg: dict, output_dir: str, max_steps: int,
    max_seq_length: int, num_samples: int, torch=None, verbose: bool = True,
):
    """Susun `SFTConfig` dari config YAML, aman terhadap perbedaan versi library.

    Semua penerjemahan nama argumen terpusat di sini supaya jalur `--check-config`
    dan training penuh memakai logika yang sama persis.
    """
    desired = dict(
        output_dir=output_dir,
        num_train_epochs=train_cfg.get("num_train_epochs", 3),
        per_device_train_batch_size=train_cfg.get("per_device_train_batch_size", 1),
        gradient_accumulation_steps=train_cfg.get("gradient_accumulation_steps", 16),
        learning_rate=float(train_cfg.get("learning_rate", 2e-4)),
        lr_scheduler_type=train_cfg.get("lr_scheduler_type", "cosine"),
        weight_decay=train_cfg.get("weight_decay", 0.01),
        max_grad_norm=train_cfg.get("max_grad_norm", 1.0),
        logging_steps=train_cfg.get("logging_steps", 10),
        save_steps=train_cfg.get("save_steps", 100),
        save_total_limit=train_cfg.get("save_total_limit", 3),
        optim=train_cfg.get("optim", "paged_adamw_8bit"),
        # Nama baru di transformers v6; `_KWARG_ALIASES` memetakan balik ke
        # `gradient_checkpointing` pada versi lama.
        activation_checkpointing=bool(train_cfg.get("gradient_checkpointing", True)),
        report_to=train_cfg.get("report_to", "none"),
        seed=int(train_cfg.get("seed", 42)),
        max_steps=max_steps,
        dataset_text_field=None,  # dataset sudah ditokenisasi
    )

    accepted = config_init_params(SFTConfig)
    notes: list[tuple[str, str]] = []

    if torch is not None:
        precision, precision_notes = resolve_precision(torch, train_cfg)
        desired.update(precision)
        notes.extend(precision_notes)
    else:
        # Mode `--check-config`: hanya memvalidasi nama argumen, jadi presisi
        # campuran tidak dipaksakan (bf16 tanpa GPU akan ditolak transformers).
        # `use_cpu` dipakai agar validasi tidak bergantung pada ketersediaan GPU.
        if "use_cpu" in accepted:
            desired["use_cpu"] = True
        desired.update({"bf16": False, "fp16": False})

    warmup, warmup_notes = resolve_warmup_kwargs(
        train_cfg, desired, num_samples, accepted
    )
    desired.update(warmup)
    notes.extend(warmup_notes)

    sft_config, dropped = build_sft_config(SFTConfig, desired, max_seq_length)

    if verbose:
        for key, reason in dropped + notes:
            print(f"[WARN] argumen '{key}' dilewati: {reason}", file=sys.stderr)
        length_name = resolve_length_kwarg(accepted) or "n/a"
        print(
            f"[INFO] {length_name:<16}: {getattr(sft_config, length_name, 'n/a')}"
            if length_name != "n/a" else "[INFO] max_length: tidak didukung",
            file=sys.stderr,
        )
        print(
            f"[INFO] presisi          : bf16={sft_config.bf16} fp16={sft_config.fp16}",
            file=sys.stderr,
        )
        print(
            f"[INFO] warmup_steps     : {getattr(sft_config, 'warmup_steps', 'n/a')}",
            file=sys.stderr,
        )

    return sft_config, dropped, notes


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
    parser.add_argument("--check-config", action="store_true",
                        help="Validasi argumen SFTConfig/SFTTrainer terhadap versi "
                             "library terpasang, tanpa memuat model atau GPU")
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

    from trl import SFTConfig, SFTTrainer

    if args.check_config:
        sft_config, dropped, notes = build_training_args(
            SFTConfig, train_cfg, output_dir, max_steps, max_seq_length,
            num_samples=0, torch=None,
        )
        tk = build_trainer_kwargs(SFTTrainer, None, sft_config, None, None)
        print("[OK] Argumen SFTConfig/SFTTrainer cocok dengan versi terpasang.")
        print(f"     SFTTrainer kwargs: {sorted(k for k in tk if k != 'model')}")
        print(f"     argumen dilewati : {[d[0] for d in dropped] or 'tidak ada'}")
        return 0

    if not torch.cuda.is_available():
        print("[WARN] CUDA tidak terdeteksi. Training QLoRA 4-bit butuh GPU NVIDIA.",
              file=sys.stderr)
        print("[WARN] Gunakan --check-config untuk memvalidasi argumen tanpa GPU.",
              file=sys.stderr)
        if not args.dry_run:
            return 3
        print("[WARN] --dry-run tetap dilanjutkan; pemuatan model 4-bit bisa gagal "
              "tanpa GPU.", file=sys.stderr)

    model, tokenizer = build_model_and_tokenizer(cfg)
    train_ds = load_dataset(dataset_path, tokenizer, max_seq_length)
    print(f"[INFO] jumlah sampel: {len(train_ds)}")

    sft_config, dropped, _ = build_training_args(
        SFTConfig, train_cfg, output_dir, max_steps, max_seq_length,
        num_samples=len(train_ds), torch=torch,
    )

    # `group_by_length` dihapus di transformers>=5 (butuh panjang sudah diketahui
    # sebelum padding). Dataset di sini sudah ter-tokenisasi, jadi panjangnya
    # dihitung langsung dan diurutkan untuk menghemat padding per batch.
    if "group_by_length" in [d[0] for d in dropped] and bool(
        train_cfg.get("group_by_length", False)
    ):
        train_ds = sort_by_length(train_ds)
        print("[INFO] group_by_length tidak didukung; dataset diurutkan per panjang.")

    trainer = SFTTrainer(
        **build_trainer_kwargs(SFTTrainer, model, sft_config, train_ds, tokenizer)
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
