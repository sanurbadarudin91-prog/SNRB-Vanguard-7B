#!/usr/bin/env python3
"""Merge LoRA adapter -> full model -> konversi ke GGUF (llama.cpp).

Alur:
  1. Merge adapter PEFT ke base model (fp16/bf16).
  2. Simpan model hasil merge ke `merged/`.
  3. Konversi ke GGUF via llama.cpp `convert_hf_to_gguf.py`.
  4. (Opsional) Kuantisasi GGUF (Q4_K_M) via `llama-quantize`.

llama.cpp tidak diinstal via pip. Clone dulu:

    git clone https://github.com/ggerganov/llama.cpp
    cd llama.cpp && cmake -B build && cmake --build build -j

Contoh:
    python src/export_gguf.py --adapter-dir outputs/snrb-vanguard-7b-qlora/final_adapter

    # dengan kuantisasi Q4_K_M
    python src/export_gguf.py --adapter-dir outputs/.../final_adapter --quantize q4_k_m

Catatan: merge 7B butuh RAM/VRAM memadai (~16-32GB). Tidak dijalankan saat
perakitan repo; hanya saat model & GPU siap.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_BASE = "Qwen/Qwen2.5-7B-Instruct"


def run(cmd: list[str], dry_run: bool = False) -> int:
    printable = " ".join(cmd)
    print(f"[CMD] {printable}")
    if dry_run:
        return 0
    return subprocess.call(cmd)


def merge_adapter(base_model: str, adapter_dir: Path, merged_dir: Path,
                  dry_run: bool) -> None:
    if dry_run:
        print(f"[DRY-RUN] merge {adapter_dir} + {base_model} -> {merged_dir}")
        return

    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    print("[INFO] memuat base model (fp16)...")
    base = AutoModelForCausalLM.from_pretrained(
        base_model, torch_dtype=torch.float16, device_map="cpu",
        trust_remote_code=True,
    )
    print("[INFO] memuat adapter...")
    model = PeftModel.from_pretrained(base, str(adapter_dir))
    print("[INFO] merge and unload...")
    model = model.merge_and_unload()

    merged_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(merged_dir), safe_serialization=True)

    tokenizer = AutoTokenizer.from_pretrained(
        str(adapter_dir), trust_remote_code=True
    )
    tokenizer.save_pretrained(str(merged_dir))
    print(f"[OK] merged model -> {merged_dir}")


def convert_to_gguf(llama_cpp_dir: Path, merged_dir: Path, outfile: Path,
                    outtype: str, dry_run: bool) -> None:
    convert_script = llama_cpp_dir / "convert_hf_to_gguf.py"
    if not convert_script.exists():
        # nama lama pada versi sebelumnya
        convert_script = llama_cpp_dir / "convert-hf-to-gguf.py"

    if not convert_script.exists() and not dry_run:
        raise FileNotFoundError(
            f"convert_hf_to_gguf.py tidak ditemukan di {llama_cpp_dir}. "
            "Pastikan llama.cpp sudah di-clone."
        )

    cmd = [
        sys.executable, str(convert_script), str(merged_dir),
        "--outfile", str(outfile), "--outtype", outtype,
    ]
    run(cmd, dry_run=dry_run)


def quantize_gguf(llama_cpp_dir: Path, gguf_f16: Path, quant: str,
                  dry_run: bool) -> Path:
    out = gguf_f16.with_name(f"{gguf_f16.stem}-{quant.upper()}.gguf")
    quantize_bin = llama_cpp_dir / "build" / "bin" / "llama-quantize"
    if not quantize_bin.exists():
        quantize_bin = llama_cpp_dir / "llama-quantize"

    cmd = [str(quantize_bin), str(gguf_f16), str(out), quant.upper()]
    run(cmd, dry_run=dry_run)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Export adapter ke GGUF")
    parser.add_argument("--base-model", default=DEFAULT_BASE)
    parser.add_argument("--adapter-dir", required=True)
    parser.add_argument("--merged-dir", default="merged/snrb-vanguard-7b")
    parser.add_argument("--llama-cpp-dir", default="llama.cpp")
    parser.add_argument("--outfile", default="outputs/snrb-vanguard-7b-f16.gguf")
    parser.add_argument("--outtype", default="f16", choices=["f16", "bf16", "f32", "q8_0"])
    parser.add_argument("--quantize", default=None,
                        help="Kuantisasi opsional: q4_k_m, q5_k_m, q8_0, dll.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Tampilkan perintah tanpa mengeksekusi")
    args = parser.parse_args()

    adapter_dir = Path(args.adapter_dir)
    if not adapter_dir.exists() and not args.dry_run:
        print(f"[ERROR] Adapter tidak ditemukan: {adapter_dir}", file=sys.stderr)
        return 2

    merged_dir = Path(args.merged_dir)
    llama_cpp_dir = Path(args.llama_cpp_dir)
    outfile = Path(args.outfile)
    outfile.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 52)
    print(" SNRB-Vanguard-7B — Export GGUF")
    print("=" * 52)

    merge_adapter(args.base_model, adapter_dir, merged_dir, args.dry_run)
    convert_to_gguf(llama_cpp_dir, merged_dir, outfile, args.outtype, args.dry_run)

    final = outfile
    if args.quantize:
        final = quantize_gguf(llama_cpp_dir, outfile, args.quantize, args.dry_run)

    print("=" * 52)
    print(f"[OK] GGUF siap: {final}")
    print("[NEXT] Jalankan lokal:")
    print(f"    ollama create snrb-vanguard-7b -f Modelfile  # FROM {final}")
    print(f"    # atau: llama-server -m {final} --port 8080")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
