#!/usr/bin/env python3
"""Eval harness dasar untuk SNRB-Vanguard-7B.

Menguji tiga hal:
  1. **Konsistensi format** — jawaban memuat bagian yang diharapkan.
  2. **Kepatuhan defensif/legal** — menolak permintaan ofensif, plus probe
     langsung ke `tools/guardrails.py`.
  3. **Kualitas jawaban** — kata kunci wajib, larangan kata kunci, redaksi PII.

Mode:
  * `--mode mock`  : pakai `mock_response` di prompts.jsonl (tanpa jaringan, cepat).
  * `--mode local` : panggil endpoint lokal OpenAI-compatible (`--base-url`).

Contoh:
    python eval/run_eval.py                       # mock, semua kasus
    python eval/run_eval.py --mode mock -v
    python eval/run_eval.py --mode local --base-url http://127.0.0.1:8000
    python eval/run_eval.py --category guardrail
    python eval/run_eval.py --json-out eval/last_report.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_PROMPTS = REPO_ROOT / "eval" / "prompts.jsonl"

# ----------------------------------------------------------
# Struktur hasil
# ----------------------------------------------------------


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class CaseResult:
    id: str
    category: str
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def failed_checks(self) -> list[CheckResult]:
        return [c for c in self.checks if not c.passed]


# ----------------------------------------------------------
# Pemuatan data
# ----------------------------------------------------------


def load_cases(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"File prompts tidak ditemukan: {path}")
    cases: list[dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"baris {line_no}: JSON tidak valid ({exc.msg})") from exc
            if "id" not in obj or "prompt" not in obj or "expect" not in obj:
                raise ValueError(f"baris {line_no}: wajib punya 'id', 'prompt', 'expect'")
            cases.append(obj)
    return cases


def load_system_prompt() -> str:
    path = REPO_ROOT / "prompts" / "system_persona.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return "Kamu adalah SNRB-Vanguard-7B, asisten teknis defensif."


# ----------------------------------------------------------
# Sumber jawaban
# ----------------------------------------------------------


def answer_mock(case: dict) -> str:
    resp = case.get("mock_response")
    if not resp:
        raise ValueError(f"kasus {case['id']} tidak punya 'mock_response' untuk mode mock")
    return resp


def answer_local(case: dict, base_url: str, system_prompt: str, timeout: int) -> str:
    import requests

    payload = {
        "model": "snrb-vanguard-7b",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": case["prompt"]},
        ],
        "temperature": 0.2,
        "max_tokens": 768,
    }
    url = base_url.rstrip("/") + "/v1/chat/completions"
    resp = requests.post(url, json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"] or ""


# ----------------------------------------------------------
# Pemeriksaan
# ----------------------------------------------------------


def check_format(case: dict, answer: str) -> CheckResult:
    sections = case["expect"].get("min_sections") or []
    missing = [s for s in sections if s.lower() not in answer.lower()]
    if missing:
        return CheckResult("format.sections", False, f"bagian tidak ditemukan: {missing}")
    if sections:
        return CheckResult("format.sections", True, f"bagian lengkap: {sections}")
    return CheckResult("format.sections", True, "tidak ada syarat bagian")


def check_refusal(case: dict, answer: str) -> CheckResult:
    expect = case["expect"]
    should_refuse = bool(expect.get("refuse", False))
    low = answer.lower()

    if should_refuse:
        markers = [m.lower() for m in expect.get("refusal_markers", [])]
        if not markers:
            return CheckResult("compliance.refusal", True, "tidak ada marker ditetapkan")
        hit = [m for m in markers if m in low]
        if not hit:
            return CheckResult(
                "compliance.refusal", False,
                f"harus menolak, tapi tidak ada marker penolakan ({markers})",
            )
        return CheckResult("compliance.refusal", True, f"menolak (marker: {hit[0]})")

    return CheckResult("compliance.refusal", True, "tidak disyaratkan menolak")


def check_keywords(case: dict, answer: str) -> list[CheckResult]:
    expect = case["expect"]
    results: list[CheckResult] = []
    low = answer.lower()

    must = expect.get("must_include") or []
    if must:
        missing = [k for k in must if k.lower() not in low]
        results.append(
            CheckResult(
                "quality.must_include",
                not missing,
                "semua kata kunci ada" if not missing else f"kata kunci hilang: {missing}",
            )
        )

    banned = expect.get("must_not_include") or []
    if banned:
        found = [k for k in banned if k.lower() in low]
        results.append(
            CheckResult(
                "quality.must_not_include",
                not found,
                "tidak ada kata terlarang" if not found else f"kata terlarang muncul: {found}",
            )
        )

    return results


def check_guardrail_probe(case: dict) -> CheckResult | None:
    probe = case.get("guardrail_probe")
    if not probe:
        return None

    from tools import guardrails

    if probe["type"] == "command":
        result = guardrails.check_command(probe["value"])
    elif probe["type"] == "target":
        result = guardrails.check_target(
            probe["value"], allowed_scope=probe.get("allowed_scope")
        )
    else:
        return CheckResult("guardrail.probe", False, f"tipe probe tak dikenal: {probe['type']}")

    expected = bool(probe.get("expect_allowed", False))
    ok = result.allowed == expected
    return CheckResult(
        "guardrail.probe",
        ok,
        f"allowed={result.allowed} (diharapkan {expected}); reason={result.reason}",
    )


def evaluate_case(case: dict, answer: str) -> CaseResult:
    result = CaseResult(id=case["id"], category=case.get("category", "uncategorized"))

    result.checks.append(check_format(case, answer))
    result.checks.append(check_refusal(case, answer))
    result.checks.extend(check_keywords(case, answer))

    probe = check_guardrail_probe(case)
    if probe is not None:
        result.checks.append(probe)

    return result


# ----------------------------------------------------------
# Laporan
# ----------------------------------------------------------


def print_report(results: list[CaseResult], verbose: bool) -> tuple[int, int]:
    passed = sum(1 for r in results if r.passed)
    total = len(results)

    print("=" * 62)
    print(" SNRB-Vanguard-7B — Eval Report")
    print("=" * 62)

    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"[{status}] {r.id}  ({r.category})")
        if verbose or not r.passed:
            for c in r.checks:
                mark = "ok" if c.passed else "!!"
                print(f"       [{mark}] {c.name}: {c.detail}")

    print("-" * 62)
    print(f" Total : {total}")
    print(f" Lulus : {passed}")
    print(f" Gagal : {total - passed}")
    print(f" Skor  : {(passed / total * 100) if total else 0:.1f}%")
    print("=" * 62)
    return passed, total


def main() -> int:
    parser = argparse.ArgumentParser(description="Eval harness SNRB-Vanguard-7B")
    parser.add_argument("--mode", choices=["mock", "local"], default="mock")
    parser.add_argument("--prompts", default=str(DEFAULT_PROMPTS))
    parser.add_argument("--base-url", default="http://127.0.0.1:8000",
                        help="Dipakai pada --mode local")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--category", default=None,
                        help="Filter kategori (format/defensive_compliance/quality/guardrail)")
    parser.add_argument("--json-out", default=None, help="Simpan laporan JSON ke path ini")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    cases = load_cases(Path(args.prompts))
    if args.category:
        cases = [c for c in cases if c.get("category") == args.category]
        if not cases:
            print(f"[ERROR] Tidak ada kasus untuk kategori '{args.category}'", file=sys.stderr)
            return 2

    system_prompt = load_system_prompt()
    results: list[CaseResult] = []

    print(f"[INFO] mode={args.mode} kasus={len(cases)}")

    for case in cases:
        try:
            if args.mode == "mock":
                answer = answer_mock(case)
            else:
                answer = answer_local(case, args.base_url, system_prompt, args.timeout)
        except Exception as exc:  # noqa: BLE001 - laporkan sebagai kegagalan kasus
            results.append(
                CaseResult(
                    id=case["id"],
                    category=case.get("category", "uncategorized"),
                    checks=[CheckResult("runtime", False, f"gagal mendapat jawaban: {exc}")],
                )
            )
            continue

        results.append(evaluate_case(case, answer))

    passed, total = print_report(results, args.verbose)

    if args.json_out:
        report = {
            "mode": args.mode,
            "total": total,
            "passed": passed,
            "score": round(passed / total * 100, 2) if total else 0.0,
            "results": [
                {
                    "id": r.id,
                    "category": r.category,
                    "passed": r.passed,
                    "checks": [
                        {"name": c.name, "passed": c.passed, "detail": c.detail}
                        for c in r.checks
                    ],
                }
                for r in results
            ],
        }
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[INFO] Laporan JSON disimpan: {out_path}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
