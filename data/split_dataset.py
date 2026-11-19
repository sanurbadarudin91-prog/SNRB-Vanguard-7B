#!/usr/bin/env python3
"""Pembagi dataset JSONL menjadi train & validation split.

Membagi `data/samples.jsonl` secara deterministik (seeded) menjadi
`data/train.jsonl` dan `data/val.jsonl`, lalu menjalankan validasi format
via `data/validate_dataset.py` pada masing-masing file.

Contoh:
    python data/split_dataset.py
    python data/split_dataset.py --input data/samples.jsonl --val-ratio 0.2 --seed 42
    python data/split_dataset.py --no-validate
"""

from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = REPO_ROOT / "data" / "samples.jsonl"
DEFAULT_TRAIN = REPO_ROOT / "data" / "train.jsonl"
DEFAULT_VAL = REPO_ROOT / "data" / "val.jsonl"
VALIDATOR = REPO_ROOT / "data" / "validate_dataset.py"


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Dataset tidak ditemukan: {path}")

    records: list[dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"baris {line_no}: JSON tidak valid ({exc.msg})") from exc
            if not isinstance(obj, dict) or "messages" not in obj:
                raise ValueError(f"baris {line_no}: tidak punya field 'messages'")
            records.append(obj)
    return records


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for obj in records:
            fh.write(json.dumps(obj, ensure_ascii=False) + "\n")


def split(records: list[dict], val_ratio: float, seed: int) -> tuple[list[dict], list[dict]]:
    if not 0.0 < val_ratio < 1.0:
        raise ValueError("--val-ratio harus di antara 0 dan 1 (eksklusif)")

    shuffled = list(records)
    random.Random(seed).shuffle(shuffled)

    val_count = max(1, round(len(shuffled) * val_ratio))
    val = shuffled[:val_count]
    train = shuffled[val_count:]

    if not train:
        raise ValueError("Split menghasilkan train kosong; perbesar dataset atau kecilkan val-ratio")

    return train, val


def run_validator(path: Path) -> int:
    print(f"\n[VALIDATE] {path.name}")
    result = subprocess.run(
        [sys.executable, str(VALIDATOR), "--path", str(path), "--show-errors"],
        capture_output=False,
    )
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Split dataset menjadi train & val")
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--train-out", default=str(DEFAULT_TRAIN))
    parser.add_argument("--val-out", default=str(DEFAULT_VAL))
    parser.add_argument("--val-ratio", type=float, default=0.2,
                        help="Proporsi data validasi (default 0.2 = 20%%)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-validate", action="store_true",
                        help="Lewati pemanggilan validate_dataset.py")
    args = parser.parse_args()

    input_path = Path(args.input)
    train_out = Path(args.train_out)
    val_out = Path(args.val_out)

    print("=" * 52)
    print(" SNRB-Vanguard-7B — Dataset Split")
    print("=" * 52)

    records = load_jsonl(input_path)
    print(f" Input        : {input_path}")
    print(f" Total sampel : {len(records)}")
    print(f" Val ratio    : {args.val_ratio:.0%} (seed={args.seed})")

    train, val = split(records, args.val_ratio, args.seed)

    write_jsonl(train_out, train)
    write_jsonl(val_out, val)

    print(f" Train        : {len(train)} sampel -> {train_out}")
    print(f" Val          : {len(val)} sampel -> {val_out}")

    # Pastikan tidak ada kebocoran: id train & val harus disjoint
    train_ids = {o.get("id") for o in train if o.get("id")}
    val_ids = {o.get("id") for o in val if o.get("id")}
    overlap = train_ids & val_ids
    if overlap:
        print(f"[ERROR] Kebocoran data: {len(overlap)} id muncul di train & val", file=sys.stderr)
        return 1
    print(f" Overlap id   : 0 (train & val disjoint)")

    print("=" * 52)

    if args.no_validate:
        print("[SKIP] Validasi dilewati (--no-validate).")
        return 0

    rc_train = run_validator(train_out)
    rc_val = run_validator(val_out)

    if rc_train != 0 or rc_val != 0:
        print("[ERROR] Validasi gagal pada salah satu split.", file=sys.stderr)
        return 1

    print("\n[OK] Split selesai & kedua file valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
