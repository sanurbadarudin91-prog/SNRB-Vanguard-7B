#!/usr/bin/env python3
"""Smoke test untuk API SNRB-Vanguard-7B.

Menguji:
  1. GET /health
  2. POST /v1/chat/completions

Bisa dijalankan dalam dua mode:
  * In-process (default): memakai FastAPI TestClient -> tidak butuh server hidup,
    tapi backend inference tetap harus aktif untuk uji chat.
  * Remote: `--base-url http://127.0.0.1:8000` untuk menembak server yang berjalan.

Contoh:
    python api/test_infer.py
    python api/test_infer.py --base-url http://127.0.0.1:8000
    python api/test_infer.py --health-only
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Pastikan root repo ada di sys.path agar `import api.server` bekerja
# saat skrip dijalankan langsung (python api/test_infer.py).
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _print(label: str, data) -> None:
    print(f"--- {label} ---")
    print(json.dumps(data, indent=2, ensure_ascii=False))


def test_inprocess(health_only: bool) -> int:
    try:
        from fastapi.testclient import TestClient
    except ImportError:
        print("[ERROR] fastapi/httpx belum terpasang.", file=sys.stderr)
        return 2

    from api.server import app

    client = TestClient(app)

    r = client.get("/health")
    _print(f"GET /health [{r.status_code}]", r.json())
    if r.status_code != 200:
        return 1

    if health_only:
        return 0

    payload = {
        "messages": [
            {"role": "system", "content": "Kamu adalah SNRB-Vanguard-7B."},
            {"role": "user", "content": "Sebutkan satu langkah defensif untuk brute-force SSH."},
        ],
        "temperature": 0.2,
        "max_tokens": 128,
    }
    r = client.post("/v1/chat/completions", json=payload)
    _print(f"POST /v1/chat/completions [{r.status_code}]", r.json())

    if r.status_code != 200:
        print("[WARN] Chat gagal — pastikan backend inference lokal aktif "
              f"(INFERENCE_BASE_URL).", file=sys.stderr)
        return 1

    body = r.json()
    assert body.get("choices"), "respons tanpa 'choices'"
    assert body["choices"][0]["message"]["content"], "konten assistant kosong"
    print("[OK] Endpoint chat mengembalikan konten valid.")
    return 0


def test_remote(base_url: str, health_only: bool) -> int:
    import requests

    base_url = base_url.rstrip("/")

    r = requests.get(f"{base_url}/health", timeout=10)
    _print(f"GET /health [{r.status_code}]", r.json())
    if r.status_code != 200:
        return 1

    if health_only:
        return 0

    payload = {
        "messages": [
            {"role": "user", "content": "Apa itu IOC dalam threat intelligence?"}
        ],
        "temperature": 0.2,
        "max_tokens": 128,
    }
    r = requests.post(f"{base_url}/v1/chat/completions", json=payload, timeout=180)
    _print(f"POST /v1/chat/completions [{r.status_code}]", r.json())
    if r.status_code != 200:
        return 1

    body = r.json()
    assert body.get("choices"), "respons tanpa 'choices'"
    print("[OK] Remote endpoint OK.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Test API SNRB-Vanguard-7B")
    parser.add_argument("--base-url", default=None,
                        help="Uji server remote; kosongkan untuk in-process")
    parser.add_argument("--health-only", action="store_true")
    args = parser.parse_args()

    if args.base_url:
        return test_remote(args.base_url, args.health_only)
    return test_inprocess(args.health_only)


if __name__ == "__main__":
    raise SystemExit(main())
