#!/usr/bin/env python3
"""Test kompatibilitas argumen SFTConfig/SFTTrainer di src/train_qlora.py.

Fokus: memastikan tidak ada `TypeError` saat `SFTConfig(**kwargs)` dipanggil,
baik di versi trl baru (`max_length`) maupun lama (`max_seq_length`).

Jalankan: python tests/test_train_qlora_compat.py
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import train_qlora as T  # noqa: E402

FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAILS.append(name)


class OldSFTConfig:
    """Tiruan trl <= 0.11 / transformers 4.x."""

    def __init__(self, output_dir=None, max_seq_length=1024, warmup_ratio=0.03,
                 gradient_checkpointing=False, group_by_length=False,
                 num_train_epochs=3, per_device_train_batch_size=1,
                 gradient_accumulation_steps=1, learning_rate=2e-4,
                 lr_scheduler_type="linear", weight_decay=0.0, max_grad_norm=1.0,
                 logging_steps=500, save_steps=500, save_total_limit=None,
                 optim="adamw_torch", report_to="none", seed=42, max_steps=-1,
                 dataset_text_field="text", bf16=False, fp16=False, **kw):
        self.max_seq_length = max_seq_length
        self.warmup_ratio = warmup_ratio
        self.group_by_length = group_by_length
        self.gradient_checkpointing = gradient_checkpointing
        self.bf16 = bf16
        self.fp16 = fp16


class OldSFTTrainer:
    """Tiruan trl <= 0.11 yang memakai `tokenizer=`."""

    def __init__(self, model=None, args=None, train_dataset=None, tokenizer=None, **kw):
        self.tokenizer = tokenizer


TRAIN_CFG = {
    "num_train_epochs": 3,
    "per_device_train_batch_size": 1,
    "gradient_accumulation_steps": 16,
    "learning_rate": 2e-4,
    "lr_scheduler_type": "cosine",
    "warmup_ratio": 0.03,
    "weight_decay": 0.01,
    "max_grad_norm": 1.0,
    "logging_steps": 10,
    "save_steps": 100,
    "save_total_limit": 3,
    "bf16": True,
    "fp16": False,
    "optim": "paged_adamw_8bit",
    "gradient_checkpointing": True,
    "group_by_length": True,
    "report_to": "none",
    "seed": 42,
}


def fake_torch(cuda_available: bool, bf16_supported: bool):
    """Pengganti torch untuk menguji pemilihan presisi tanpa GPU nyata."""
    return types.SimpleNamespace(
        cuda=types.SimpleNamespace(
            is_available=lambda: cuda_available,
            is_bf16_supported=lambda: bf16_supported,
        ),
        bfloat16="bf16",
        float16="fp16",
    )


print("=== 1. Helper dasar ===")
check("config_init_params membaca signature",
      "output_dir" in T.config_init_params(OldSFTConfig))
check("resolve_length_kwarg -> max_seq_length (versi lama)",
      T.resolve_length_kwarg(T.config_init_params(OldSFTConfig)) == "max_seq_length")
check("resolve_length_kwarg -> max_length (versi baru)",
      T.resolve_length_kwarg({"max_length", "output_dir"}) == "max_length")

print("\n=== 2. Kompatibilitas versi lama (alias dipetakan, bukan dibuang) ===")
cfg_old, dropped_old, _ = T.build_training_args(
    OldSFTConfig, TRAIN_CFG, "/tmp/out", 3, 512,
    num_samples=802, torch=None, verbose=False,
)
check("versi lama: max_seq_length=512", getattr(cfg_old, "max_seq_length", None) == 512)
check("versi lama: warmup_ratio diteruskan", getattr(cfg_old, "warmup_ratio", None) == 0.03)
check("versi lama: activation_checkpointing -> gradient_checkpointing",
      getattr(cfg_old, "gradient_checkpointing", None) is True)
check("versi lama: tidak ada argumen dibuang", dropped_old == [], str(dropped_old))

tk_old = T.build_trainer_kwargs(OldSFTTrainer, "M", cfg_old, "D", "TOK")
check("versi lama: SFTTrainer memakai tokenizer=",
      tk_old.get("tokenizer") == "TOK" and "processing_class" not in tk_old)

print("\n=== 3. Pemilihan presisi (T4 tidak mendukung bfloat16) ===")
prec_t4, notes_t4 = T.resolve_precision(fake_torch(True, False), {"bf16": True})
check("T4: bf16 diturunkan ke fp16", prec_t4 == {"bf16": False, "fp16": True}, str(prec_t4))
check("T4: penurunan dilaporkan", any(n[0] == "bf16" for n in notes_t4))

prec_a100, _ = T.resolve_precision(fake_torch(True, True), {"bf16": True})
check("A100: bf16 dipertahankan", prec_a100 == {"bf16": True, "fp16": False}, str(prec_a100))

prec_cpu, _ = T.resolve_precision(fake_torch(False, False), {"bf16": True})
check("CPU: presisi campuran dimatikan",
      prec_cpu == {"bf16": False, "fp16": False}, str(prec_cpu))

check("T4: compute dtype bfloat16 -> float16",
      T.resolve_compute_dtype(fake_torch(True, False), "bfloat16") == "fp16")
check("A100: compute dtype bfloat16 dipertahankan",
      T.resolve_compute_dtype(fake_torch(True, True), "bfloat16") == "bf16")

print("\n=== 4. warmup_ratio -> warmup_steps ===")
steps, _ = T.resolve_warmup_kwargs(
    {"warmup_ratio": 0.03}, {"max_steps": 100}, 802, {"warmup_steps"})
check("warmup_ratio 0.03 x 100 step = 3", steps == {"warmup_steps": 3}, str(steps))

steps, _ = T.resolve_warmup_kwargs(
    {"warmup_ratio": 0.03},
    {"max_steps": -1, "num_train_epochs": 3,
     "per_device_train_batch_size": 1, "gradient_accumulation_steps": 16},
    802, {"warmup_steps"},
)
# 802 / (1x16) = 51 step/epoch, x3 epoch = 153 step, 3% ~= 5 step
check("warmup dihitung dari epoch saat max_steps=-1",
      steps == {"warmup_steps": 5}, str(steps))

print("\n=== 5. Versi trl terpasang (uji signature nyata) ===")
try:
    from trl import SFTConfig, SFTTrainer

    cfg_new, dropped_new, _ = T.build_training_args(
        SFTConfig, TRAIN_CFG, "/tmp/out", 3, 512,
        num_samples=802, torch=None, verbose=False,
    )
    check("trl terpasang: max_length=512",
          getattr(cfg_new, "max_length", None) == 512,
          str(getattr(cfg_new, "max_length", None)))
    check("trl terpasang: tidak ada argumen dibuang", dropped_new == [], str(dropped_new))

    tk_new = T.build_trainer_kwargs(SFTTrainer, "M", cfg_new, "D", "TOK")
    check("trl terpasang: SFTTrainer memakai processing_class",
          tk_new.get("processing_class") == "TOK")
except ImportError:
    print("[INFO] trl tidak terpasang; uji signature nyata dilewati.")

print()
if FAILS:
    print(f"GAGAL: {len(FAILS)} cek -> {FAILS}")
    raise SystemExit(1)
print("SEMUA CEK LOLOS")
