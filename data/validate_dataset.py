#!/usr/bin/env python3
"""Validator dataset JSONL untuk SNRB-Vanguard-7B.

Memeriksa struktur `messages`, urutan & nilai `role`, menghitung baris
valid/tidak valid, serta menampilkan statistik panjang karakter dan
estimasi jumlah token.

Contoh pemakaian:
    python data/validate_dataset.py --path data/samples.jsonl
    python data/validate_dataset.py --path data/samples.jsonl --strict --show-errors
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

VALID_ROLES = {"system", "user", "assistant"}
REQUIRED_ROLES = {"user", "assistant"}

# Estimasi kasar: ~4 karakter per token untuk teks campuran Inggris/Indonesia.
# Cukup untuk sanity-check ukuran dataset, bukan untuk billing.
CHARS_PER_TOKEN = 4


@dataclass
class Stats:
    total_lines: int = 0
    valid: int = 0
    invalid: int = 0
    empty_lines: int = 0
    total_chars: int = 0
    total_tokens_est: int = 0
    min_tokens: int = sys.maxsize
    max_tokens: int = 0
    errors: list[str] = field(default_factory=list)


def validate_sample(obj: object, line_no: int) -> tuple[bool, int, str | None]:
    """Validasi satu objek sample. Kembalikan (valid, token_est, error)."""
    if not isinstance(obj, dict):
        return False, 0, "baris bukan objek JSON"

    messages = obj.get("messages")
    if not isinstance(messages, list) or not messages:
        return False, 0, "field 'messages' harus list dan tidak kosong"

    seen_roles: set[str] = set()
    chars = 0
    for idx, msg in enumerate(messages):
        if not isinstance(msg, dict):
            return False, 0, f"messages[{idx}] bukan objek"
        role = msg.get("role")
        content = msg.get("content")
        if role not in VALID_ROLES:
            return False, 0, f"messages[{idx}].role tidak valid: {role!r}"
        if not isinstance(content, str) or not content.strip():
            return False, 0, f"messages[{idx}].content kosong/bukan string"
        seen_roles.add(role)
        chars += len(content)

    missing = REQUIRED_ROLES - seen_roles
    if missing:
        return False, 0, f"role wajib tidak ada: {sorted(missing)}"

    if messages[-1].get("role") != "assistant":
        return False, 0, "pesan terakhir harus berperan 'assistant'"

    return True, max(1, chars // CHARS_PER_TOKEN), None


def run(path: Path, strict: bool, show_errors: bool) -> int:
    stats = Stats()

    if not path.exists():
        print(f"[ERROR] File tidak ditemukan: {path}", file=sys.stderr)
        return 2

    with path.open("r", encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, start=1):
            stats.total_lines += 1
            line = raw.strip()
            if not line:
                stats.empty_lines += 1
                continue

            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                stats.invalid += 1
                msg = f"baris {line_no}: JSON tidak valid ({exc.msg})"
                stats.errors.append(msg)
                continue

            ok, tokens, err = validate_sample(obj, line_no)
            if not ok:
                stats.invalid += 1
                stats.errors.append(f"baris {line_no}: {err}")
                continue

            stats.valid += 1
            chars = sum(len(m["content"]) for m in obj["messages"])
            stats.total_chars += chars
            stats.total_tokens_est += tokens
            stats.min_tokens = min(stats.min_tokens, tokens)
            stats.max_tokens = max(stats.max_tokens, tokens)

    print("=" * 52)
    print(" SNRB-Vanguard-7B — Dataset Validation Report")
    print("=" * 52)
    print(f" File               : {path}")
    print(f" Total baris        : {stats.total_lines}")
    print(f" Baris kosong       : {stats.empty_lines}")
    print(f" Baris valid        : {stats.valid}")
    print(f" Baris tidak valid  : {stats.invalid}")

    if stats.valid:
        avg_chars = stats.total_chars // stats.valid
        avg_tokens = stats.total_tokens_est // stats.valid
        print(f" Total karakter     : {stats.total_chars:,}")
        print(f" Rata-rata karakter : {avg_chars:,}/sampel")
        print(f" Estimasi token     : {stats.total_tokens_est:,} total "
              f"(~{avg_tokens:,}/sampel)")
        print(f" Token min/max      : {stats.min_tokens:,} / {stats.max_tokens:,}")
        print(f" Asumsi             : ~{CHARS_PER_TOKEN} karakter/token")

    if stats.errors and show_errors:
        print("-" * 52)
        print(" Detail error:")
        for err in stats.errors:
            print(f"   - {err}")

    print("=" * 52)

    if stats.invalid:
        return 1
    if stats.valid == 0:
        print("[ERROR] Tidak ada baris valid.", file=sys.stderr)
        return 1
    if strict and stats.empty_lines:
        print("[ERROR] --strict: ditemukan baris kosong.", file=sys.stderr)
        return 1

    print("[OK] Dataset valid.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validasi dataset JSONL untuk fine-tuning SNRB-Vanguard-7B."
    )
    parser.add_argument("--path", required=True, help="Path ke file .jsonl")
    parser.add_argument("--strict", action="store_true",
                        help="Gagal bila ada baris kosong")
    parser.add_argument("--show-errors", action="store_true",
                        help="Tampilkan detail setiap error")
    args = parser.parse_args()

    return run(Path(args.path), args.strict, args.show_errors)


if __name__ == "__main__":
    raise SystemExit(main())
