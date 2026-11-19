#!/usr/bin/env python3
"""Konversi dataset JSONL ke chat template Qwen2.5-Instruct.

Membaca dataset berformat `messages` (system/user/assistant), menerapkan chat
template `Qwen/Qwen2.5-7B-Instruct` secara konsisten, lalu memeriksa panjang
token setiap sampel terhadap `data.max_seq_length` pada konfigurasi QLoRA.

Tidak menyentuh bobot model sama sekali — hanya tokenizer yang dimuat.

Contoh pemakaian:
    # Tokenizer asli (akurat), fallback ke estimasi bila offline
    python data/format_chat.py --input data/train.jsonl --output data/train.chat.jsonl

    # Paksa mode estimasi (tanpa jaringan / tanpa transformers)
    python data/format_chat.py --input data/train.jsonl --offline

    # Gagal bila ada sampel melebihi max_seq_length (gate CI)
    python data/format_chat.py --input data/train.jsonl --strict

    # Ganti system prompt dengan persona dari file
    python data/format_chat.py --input data/train.jsonl --persona prompts/system_persona.md
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Estimasi konservatif untuk mode offline. Tokenizer Qwen2.5 menghasilkan
# ~3,1 karakter/token pada dataset ini, jadi 3 dipakai agar estimasi tidak
# pernah lebih rendah dari jumlah token sebenarnya (aman untuk gate --strict).
CHARS_PER_TOKEN = 3


# ----------------------------------------------------------------------
# Konfigurasi
# ----------------------------------------------------------------------
def load_config(path: Path) -> dict:
    """Baca konfigurasi YAML. Kembalikan dict kosong bila file tidak ada."""
    if not path.exists():
        return {}
    try:
        import yaml
    except ImportError:
        print(f"[WARN] pyyaml tidak tersedia, abaikan {path}", file=sys.stderr)
        return {}
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def resolve_persona(text: str) -> str:
    """Ambil isi persona dari markdown, buang heading & komentar.

    Persona dipakai apa adanya sebagai system prompt agar identitas model
    konsisten dengan `prompts/system_persona.md`.
    """
    lines = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("#"):
            continue
        if line.startswith("<!--"):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


# ----------------------------------------------------------------------
# Tokenizer
# ----------------------------------------------------------------------
class TokenCounter:
    """Penghitung token: tokenizer asli Qwen bila tersedia, jika tidak estimasi."""

    def __init__(self, model_name: str, offline: bool) -> None:
        self.model_name = model_name
        self.tokenizer = None
        self.mode = "estimate"

        if offline:
            return
        try:
            import transformers
            from transformers import AutoTokenizer

            # Tokenizer-only: torch tidak dibutuhkan, jangan berisik di log CI.
            transformers.logging.set_verbosity_error()
        except ImportError:
            print(
                "[WARN] transformers tidak terpasang -> memakai estimasi "
                f"~{CHARS_PER_TOKEN} karakter/token.",
                file=sys.stderr,
            )
            return

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name, trust_remote_code=True
            )
            self.mode = "tokenizer"
        except Exception as exc:  # noqa: BLE001 - alasan apa pun -> fallback
            print(
                f"[WARN] gagal memuat tokenizer '{model_name}' ({exc.__class__.__name__}). "
                "Memakai estimasi.",
                file=sys.stderr,
            )

    def render(self, messages: list[dict]) -> str:
        """Terapkan chat template Qwen; fallback ke format manual bila perlu."""
        if self.tokenizer is not None and getattr(self.tokenizer, "chat_template", None):
            return self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=False
            )
        # Fallback: format ChatML yang sama dengan template Qwen2.5
        parts = []
        for msg in messages:
            parts.append(f"<|im_start|>{msg['role']}\n{msg['content']}<|im_end|>")
        return "\n".join(parts) + "\n"

    def count(self, text: str) -> int:
        if self.tokenizer is not None:
            return len(self.tokenizer(text, add_special_tokens=False)["input_ids"])
        return max(1, len(text) // CHARS_PER_TOKEN)


# ----------------------------------------------------------------------
# Statistik
# ----------------------------------------------------------------------
@dataclass
class Report:
    input_path: str = ""
    output_path: str = ""
    tokenizer_mode: str = "estimate"
    max_seq_length: int = 0
    total: int = 0
    written: int = 0
    overflow: int = 0
    invalid: int = 0
    min_tokens: int = sys.maxsize
    max_tokens: int = 0
    lengths: list[int] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def add(self, tokens: int) -> None:
        self.lengths.append(tokens)
        self.min_tokens = min(self.min_tokens, tokens)
        self.max_tokens = max(self.max_tokens, tokens)

    def summary(self) -> dict:
        if not self.lengths:
            return {}
        ordered = sorted(self.lengths)
        return {
            "count": len(ordered),
            "min": ordered[0],
            "max": ordered[-1],
            "mean": round(statistics.fmean(ordered), 1),
            "p50": ordered[int(len(ordered) * 0.50)],
            "p95": ordered[min(int(len(ordered) * 0.95), len(ordered) - 1)],
            "p99": ordered[min(int(len(ordered) * 0.99), len(ordered) - 1)],
            "total": sum(ordered),
        }


# ----------------------------------------------------------------------
# Proses utama
# ----------------------------------------------------------------------
def process(
    input_path: Path,
    output_path: Path | None,
    counter: TokenCounter,
    max_seq_length: int,
    persona: str | None,
    limit: int | None,
) -> Report:
    report = Report(
        input_path=str(input_path),
        output_path=str(output_path) if output_path else "(tidak ditulis)",
        tokenizer_mode=counter.mode,
        max_seq_length=max_seq_length,
    )

    if not input_path.exists():
        raise FileNotFoundError(f"Dataset tidak ditemukan: {input_path}")

    out_lines: list[str] = []

    with input_path.open(encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, start=1):
            if limit is not None and report.total >= limit:
                break
            line = raw.strip()
            if not line:
                continue
            report.total += 1

            try:
                obj = json.loads(line)
                messages = obj["messages"]
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                report.invalid += 1
                report.errors.append(f"baris {line_no}: {exc}")
                continue

            if persona:
                messages = [
                    {"role": "system", "content": persona}
                    if m.get("role") == "system"
                    else m
                    for m in messages
                ]

            text = counter.render(messages)
            tokens = counter.count(text)
            report.add(tokens)

            if tokens > max_seq_length:
                report.overflow += 1
                report.errors.append(
                    f"baris {line_no} (id={obj.get('id', '?')}): "
                    f"{tokens} token > max_seq_length {max_seq_length}"
                )

            record = {
                "id": obj.get("id"),
                "n_tokens": tokens,
                "text": text,
            }
            out_lines.append(json.dumps(record, ensure_ascii=False))

    report.written = len(out_lines)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

    return report


def verify_sync(
    input_path: Path,
    chat_path: Path,
    counter: TokenCounter,
    persona: str | None,
) -> int:
    """Bandingkan hasil render ulang dengan file chat yang sudah ada.

    Hanya field `text` yang dibandingkan, sehingga verifikasi bisa dijalankan
    dalam mode offline (tanpa tokenizer) dan tetap deterministik.
    """
    if not chat_path.exists():
        print(f"[ERROR] File chat tidak ditemukan: {chat_path}", file=sys.stderr)
        return 2

    existing = []
    with chat_path.open(encoding="utf-8") as fh:
        for raw in fh:
            if raw.strip():
                existing.append(json.loads(raw))

    mismatches = []
    count = 0
    with input_path.open(encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, start=1):
            if not raw.strip():
                continue
            obj = json.loads(raw)
            messages = obj["messages"]
            if persona:
                messages = [
                    {"role": "system", "content": persona}
                    if m.get("role") == "system"
                    else m
                    for m in messages
                ]
            expected = counter.render(messages)
            idx = count
            count += 1
            if idx >= len(existing):
                mismatches.append(f"baris {line_no}: tidak ada padanan di file chat")
                continue
            if existing[idx].get("text") != expected:
                mismatches.append(f"baris {line_no} (id={obj.get('id', '?')}): teks berbeda")

    if len(existing) > count:
        mismatches.append(
            f"file chat punya {len(existing)} entri, sumber hanya {count}"
        )

    print("=" * 60)
    print(" SNRB-Vanguard-7B — Chat Template Sync Check")
    print("=" * 60)
    print(f" Sumber           : {input_path} ({count} entri)")
    print(f" File chat        : {chat_path} ({len(existing)} entri)")
    print(f" Mode render      : {counter.mode}")
    print(f" Tidak sinkron    : {len(mismatches)}")
    if mismatches:
        print("-" * 60)
        for msg in mismatches[:20]:
            print(f"   - {msg}")
        if len(mismatches) > 20:
            print(f"   ... dan {len(mismatches) - 20} lainnya")
        print("=" * 60)
        print("[ERROR] File chat tidak sinkron. Jalankan ulang data/format_chat.py.",
              file=sys.stderr)
        return 1
    print("=" * 60)
    print("[OK] File chat sinkron dengan sumber.")
    return 0


def print_report(report: Report) -> None:
    stats = report.summary()
    print("=" * 60)
    print(" SNRB-Vanguard-7B — Chat Template Formatting Report")
    print("=" * 60)
    print(f" Input            : {report.input_path}")
    print(f" Output           : {report.output_path}")
    print(f" Tokenizer        : {report.tokenizer_mode}")
    print(f" max_seq_length   : {report.max_seq_length}")
    print(f" Total baris      : {report.total}")
    print(f" Ditulis          : {report.written}")
    print(f" Tidak valid      : {report.invalid}")
    print(f" Melebihi batas   : {report.overflow}")
    if stats:
        print("-" * 60)
        print(f" Token min        : {stats['min']:,}")
        print(f" Token max        : {stats['max']:,}")
        print(f" Token rata-rata  : {stats['mean']:,}")
        print(f" Token p50/p95    : {stats['p50']:,} / {stats['p95']:,}")
        print(f" Token p99        : {stats['p99']:,}")
        print(f" Total token      : {stats['total']:,}")
        if report.max_seq_length:
            headroom = report.max_seq_length - stats["max"]
            pct = 100.0 * stats["max"] / report.max_seq_length
            print(f" Headroom         : {headroom:,} token "
                  f"(pemakaian tertinggi {pct:.1f}% dari batas)")
    if report.errors:
        print("-" * 60)
        print(" Detail:")
        for err in report.errors[:20]:
            print(f"   - {err}")
        if len(report.errors) > 20:
            print(f"   ... dan {len(report.errors) - 20} lainnya")
    print("=" * 60)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Konversi dataset messages -> chat template Qwen2.5-Instruct."
    )
    parser.add_argument("--input", required=True, help="File JSONL sumber")
    parser.add_argument("--output", default=None,
                        help="File JSONL hasil (default: <input>.chat.jsonl)")
    parser.add_argument("--config", default="configs/qlora_default.yaml",
                        help="Konfigurasi QLoRA (untuk max_seq_length & base_model)")
    parser.add_argument("--max-seq-length", type=int, default=None,
                        help="Override max_seq_length dari konfigurasi")
    parser.add_argument("--tokenizer", default=None,
                        help="Nama model tokenizer (default: model.base_model di config)")
    parser.add_argument("--persona", default=None,
                        help="Ganti system prompt dengan isi file markdown ini")
    parser.add_argument("--offline", action="store_true",
                        help="Paksa mode estimasi tanpa memuat tokenizer")
    parser.add_argument("--strict", action="store_true",
                        help="Exit 1 bila ada sampel melebihi max_seq_length")
    parser.add_argument("--no-write", action="store_true",
                        help="Hanya analisis, jangan tulis output")
    parser.add_argument("--limit", type=int, default=None,
                        help="Batasi jumlah baris yang diproses")
    parser.add_argument("--report", default=None,
                        help="Simpan laporan statistik ke file JSON")
    parser.add_argument("--verify", action="store_true",
                        help="Hanya verifikasi file chat sudah sinkron dengan sumber "
                             "(tidak menulis apa pun; cocok untuk CI)")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    model_name = args.tokenizer or (cfg.get("model", {}) or {}).get(
        "base_model", "Qwen/Qwen2.5-7B-Instruct"
    )
    max_seq_length = args.max_seq_length or int(
        (cfg.get("data", {}) or {}).get("max_seq_length", 2048)
    )

    persona = None
    if args.persona:
        persona_path = Path(args.persona)
        if not persona_path.exists():
            print(f"[ERROR] File persona tidak ditemukan: {persona_path}", file=sys.stderr)
            return 2
        persona = resolve_persona(persona_path.read_text(encoding="utf-8"))

    input_path = Path(args.input)
    output_path = None if args.no_write else Path(
        args.output or input_path.with_suffix(".chat.jsonl")
    )

    counter = TokenCounter(model_name, offline=args.offline)

    if args.verify:
        if output_path is None:
            print("[ERROR] --verify membutuhkan path file chat (jangan pakai --no-write).",
                  file=sys.stderr)
            return 2
        try:
            return verify_sync(input_path, output_path, counter, persona)
        except FileNotFoundError as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            return 2

    try:
        report = process(
            input_path=input_path,
            output_path=output_path,
            counter=counter,
            max_seq_length=max_seq_length,
            persona=persona,
            limit=args.limit,
        )
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2

    print_report(report)

    if args.report:
        payload = {
            "input": report.input_path,
            "output": report.output_path,
            "tokenizer_mode": report.tokenizer_mode,
            "max_seq_length": report.max_seq_length,
            "total": report.total,
            "written": report.written,
            "invalid": report.invalid,
            "overflow": report.overflow,
            "stats": report.summary(),
        }
        Path(args.report).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"[INFO] Laporan JSON disimpan: {args.report}")

    if report.invalid:
        print("[ERROR] Ada baris tidak valid.", file=sys.stderr)
        return 1
    if args.strict and report.overflow:
        print(
            f"[ERROR] --strict: {report.overflow} sampel melebihi "
            f"max_seq_length {max_seq_length}.",
            file=sys.stderr,
        )
        return 1

    print("[OK] Konversi chat template selesai.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
