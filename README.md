# SNRB-Vanguard-7B

[![CI](https://github.com/sanurbadarudin91-prog/SNRB-Vanguard-7B/actions/workflows/ci.yml/badge.svg)](https://github.com/sanurbadarudin91-prog/SNRB-Vanguard-7B/actions/workflows/ci.yml)

> Asisten teknis 7B yang di-fine-tune dengan QLoRA untuk **analisis defensif**:
> analisis log/kode, hardening, triase insiden, dan OSINT legal dari sumber terbuka.

Repo ini adalah **kerangka lengkap** yang bisa dirakit tanpa GPU: semua skrip,
konfigurasi, dan struktur siap, dan training baru dijalankan saat GPU aktif.

---

## Arsitektur

```
 ┌─────────────────┐   ┌──────────────────────┐   ┌────────────────────┐
 │  Data & Persona │──▶│ QLoRA Fine-tuning    │──▶│ Export GGUF        │
 │  data/*.jsonl   │   │ src/train_qlora.py   │   │ src/export_gguf.py │
 │  prompts/*.md   │   │ configs/*.yaml       │   │ (merge + quantize) │
 └─────────────────┘   └──────────────────────┘   └────────────────────┘
                                                             │
                                                             ▼
 ┌─────────────────────┐   ┌──────────────────────┐   ┌────────────────────┐
 │ Workflows & Skills  │◀──│ Guardrails           │◀──│ Local Inference    │
 │ workflows/, skills/ │   │ tools/guardrails.py  │   │ api/server.py      │
 └─────────────────────┘   └──────────────────────┘   │ (OpenAI-compat)    │
                                                       └────────────────────┘
```

**Alur:** data & persona → QLoRA fine-tuning → export GGUF → API inference lokal
bergaya OpenAI → dipakai oleh workflows, skills, dan guardrails.

---

## Struktur Repository

```
SNRB-Vanguard-7B/
├── README.md
├── requirements.txt          # dipisah: [CORE] API/validasi & [TRAINING/GPU]
├── .gitignore
├── .github/
│   └── workflows/
│       └── ci.yml            # CI: sintaks + validasi + split + eval mock
├── data/
│   ├── samples.jsonl         # dataset utama (537 sampel, format messages)
│   ├── train.jsonl           # split training (dihasilkan split_dataset.py)
│   ├── val.jsonl             # split validasi (dihasilkan split_dataset.py)
│   ├── train.chat.jsonl      # train + chat template Qwen (format_chat.py)
│   ├── val.chat.jsonl        # val + chat template Qwen (format_chat.py)
│   ├── validate_dataset.py   # validator JSONL + statistik token
│   ├── split_dataset.py      # pembagi train/val deterministik (seeded)
│   └── format_chat.py        # konversi chat template Qwen + cek max_seq_length
├── prompts/
│   └── system_persona.md     # aturan main & gaya komunikasi
├── configs/
│   └── qlora_default.yaml    # konfigurasi QLoRA (Qwen2.5-7B-Instruct)
├── src/
│   ├── train_qlora.py        # CLI training (--config, --dataset, --dry-run)
│   └── export_gguf.py        # merge adapter → GGUF (llama.cpp)
├── api/
│   ├── schemas.py            # model Pydantic
│   ├── server.py             # FastAPI: /health, /v1/chat/completions
│   └── test_infer.py         # smoke test endpoint
├── eval/
│   ├── prompts.jsonl         # 12 kasus uji (format/compliance/quality/guardrail)
│   └── run_eval.py           # eval harness (--mode mock | local)
├── workflows/
│   ├── code_audit.md
│   └── defensive_osint_report.md
├── skills/
│   ├── log_triage.md
│   ├── prompt_adapter.md
│   ├── staged_planning.md    # perencanaan bertahap + rollback
│   └── findings_summary.md   # ringkasan temuan teknis berprioritas
└── tools/
    └── guardrails.py         # pembatas perintah/target (defensif & legal)
```

---

## Quickstart (tanpa GPU)

```bash
# 1. Dependensi ringan (API + validasi)
pip install fastapi uvicorn pydantic pyyaml requests transformers jinja2

# 2. Validasi dataset
python data/validate_dataset.py --path data/samples.jsonl --show-errors

# 3. Bagi dataset jadi train & val (sekaligus validasi keduanya)
python data/split_dataset.py

# 4. Eval harness — mode mock (tanpa jaringan)
python eval/run_eval.py --mode mock

# 5. Cek guardrails (demo)
python tools/guardrails.py

# 6. Jalankan API (butuh backend inference lokal, mis. Ollama)
export INFERENCE_BASE_URL=http://127.0.0.1:11434
export MODEL_NAME=snrb-vanguard-7b
uvicorn api.server:app --host 0.0.0.0 --port 8000

# 7. Eval terhadap endpoint lokal
python eval/run_eval.py --mode local --base-url http://127.0.0.1:8000
```

---

## Dataset & Split

`data/samples.jsonl` berisi **537 contoh** percakapan format `messages`
(`system` → `user` → `assistant`) yang konsisten dengan persona:
analisis log/kode, hardening, triase insiden, arsitektur sistem, dan OSINT legal.

| Metrik | Nilai |
|---|---|
| Total sampel | **537** |
| Total karakter | ~527.216 |
| Estimasi token | ~131.606 (~245/sampel) |
| Panjang token min/max | 161 / 307 |
| Duplikat id / prompt | **0** |

**Cakupan topik** — keamanan aplikasi (injection, SSRF, deserialization, upload,
path traversal, race condition, mass assignment, open redirect, CSRF, XXE,
SSTI, prototype pollution, request smuggling, cache poisoning), keamanan cloud
(AWS/Azure/GCP, IAM least privilege, jalur privesc, S3 Block Public Access,
Lambda, CloudFront origin, audit logging, cost anomaly, cryptomining), container
& Kubernetes (image hardening, resource limit, probe, RBAC, network policy,
seccomp/AppArmor, HPA, PDB, escape detection), jaringan (nginx/Apache hardening,
TLS/cipher, HSTS, OCSP stapling, WAF tuning, DNS filtering, egress filtering,
IDS placement, segmentation), data & database (RLS, EXPLAIN, pooling, replika
lag, shard key, migrasi tanpa downtime, masking, retensi, PII discovery),
identitas (OAuth/PKCE, SAML vs OIDC, JWT vs session, revokasi JWT, MFA rollout,
PAM, break-glass, conditional access, SSO/SCIM), deteksi & respons (SIEM,
detection engineering, threat hunting, purple team, triage 4625/Sysmon, timeline,
containment, ransomware, insider threat, BEC, DLP/UBA), forensik (chain of
custody, integritas image, memori, YARA, sandbox, kit phishing), kriptografi
(envelope/KMS, rotasi, mTLS, password storage, crypto-agility, pasca-kuantum),
AI/LLM security (prompt injection, RAG, tool permission, model supply chain,
output guardrail), kepatuhan (GDPR/CCPA, SOC 2, ISO 27001, PCI DSS scope,
NIST CSF, CIS benchmark), serta arsitektur & operasi (SLO, capacity planning,
DR test, zero-downtime, canary/blue-green, GitOps, IaC scanning, observability),
**mobile** (izin Android, komponen exported, Keychain iOS, pinning, deeplink,
WebView), **Active Directory** (kerberoasting, AS-REP, DCSync, Golden Ticket,
spraying, GPO/LAPS, LDAP signing, tiered admin, gMSA), **Windows internals**
(LSASS protection, LOLBin, WMI/scheduled task/registry persistence, DLL
sideloading, AppLocker vs WDAC, Credential Guard), **Linux internals**
(systemd hardening, cgroup, namespace, capabilities, SELinux/AppArmor, kernel
update, sshd lanjutan, auditd), **jaringan lanjutan** (BGP hijack, DNSSEC,
IPv6, DHCP snooping, ARP spoofing, VLAN, tap placement, TLS inspection),
**OT/ICS** (zona IEC 62443, patch PLC, remote access SCADA, integritas
firmware), serta **rekayasa & proses** (pola Go/Python/concurrency, Dockerfile
multi-stage, graceful shutdown, saga/outbox/CQRS, distributed lock, SQL
performance, ReDoS, integer overflow, TOCTOU, logika bisnis, supply chain,
SBOM, lisensi, risk register, vendor assessment).

**Pembagian train/val** (deterministik, `--seed 42`, `--val-ratio 0.2`):

```bash
python data/split_dataset.py            # -> data/train.jsonl (430) + data/val.jsonl (107)
python data/split_dataset.py --val-ratio 0.15 --seed 7
python data/split_dataset.py --no-validate
```

Skrip ini menjamin **tidak ada kebocoran id** antara train & val (dicek
otomatis), lalu memanggil `validate_dataset.py` pada kedua file.

---

## Chat Template Qwen (siap QLoRA)

`data/format_chat.py` mengubah dataset `messages` menjadi teks siap latih dengan
chat template resmi `Qwen/Qwen2.5-7B-Instruct`, lalu memeriksa panjang token
terhadap `data.max_seq_length` di `configs/qlora_default.yaml` (**2048**).
Skrip ini **hanya memuat tokenizer** — tidak menyentuh bobot model, tidak butuh
GPU, dan tidak butuh API berbayar.

```bash
# Konversi (menulis data/train.chat.jsonl & data/val.chat.jsonl)
python data/format_chat.py --input data/train.jsonl
python data/format_chat.py --input data/val.jsonl

# Gate CI: gagal bila ada sampel melebihi max_seq_length
python data/format_chat.py --input data/train.jsonl --no-write --strict

# Pastikan file .chat.jsonl yang di-commit masih sinkron dengan sumbernya
python data/format_chat.py --input data/train.jsonl --verify

# Tanpa jaringan / tanpa transformers (estimasi konservatif 3 char/token)
python data/format_chat.py --input data/train.jsonl --offline

# Ganti system prompt dengan persona dari file
python data/format_chat.py --input data/train.jsonl --persona prompts/system_persona.md
```

Output berformat JSONL dengan tiga field: `id`, `n_tokens`, dan `text` (hasil
`apply_chat_template` dengan `<|im_start|>`/`<|im_end|>` ChatML Qwen).

**Hasil pada dataset saat ini** (tokenizer asli, `max_seq_length=2048`):

| Split | Entri | Token min | Token max | Rata-rata | p95 | Total token | Pemakaian batas |
|---|---|---|---|---|---|---|---|
| `train.chat.jsonl` | 430 | 219 | **400** | 318,6 | 367 | 137.019 | **19,5 %** |
| `val.chat.jsonl` | 107 | 259 | **408** | 321,2 | 379 | 34.368 | **19,9 %** |

Tidak ada sampel yang terpotong (`Melebihi batas: 0`) — headroom ~1.640 token
pada sampel terpanjang. Artinya `max_seq_length: 2048` aman; bahkan bisa
diturunkan ke 512 untuk menghemat VRAM tanpa kehilangan data.

---

## Eval Harness

`eval/run_eval.py` menguji tiga dimensi pada 12 kasus di `eval/prompts.jsonl`:

| Dimensi | Yang diperiksa |
|---|---|
| `format` | Jawaban memuat bagian wajib (mis. `Ringkasan`, `Langkah`) |
| `defensive_compliance` | Menolak permintaan ofensif dengan marker penolakan |
| `quality` | Kata kunci wajib ada, kata terlarang tidak muncul, redaksi PII |
| `guardrail` | Probe langsung ke `tools/guardrails.py` (perintah & scope target) |

Mode:

```bash
python eval/run_eval.py --mode mock                     # pakai mock_response, tanpa jaringan
python eval/run_eval.py --mode local --base-url http://127.0.0.1:8000
python eval/run_eval.py --category guardrail -v
python eval/run_eval.py --json-out eval/last_report.json
```

Exit code `0` bila semua lulus, `1` bila ada kegagalan — siap dipakai sebagai
gate di CI.

---

## Continuous Integration

Workflow: [`.github/workflows/ci.yml`](.github/workflows/ci.yml) — berjalan otomatis
pada **push** dan **pull_request** ke `main` (juga bisa dijalankan manual via
`workflow_dispatch`).

| Job | Langkah | Tujuan |
|---|---|---|
| `syntax` | `compileall` (api/data/eval/src/tools) | Semua modul Python bisa dikompilasi |
| `syntax` | YAML check (`configs/`, `.github/`) | Semua YAML valid & parseable |
| `syntax` | JSON/JSONL check (seluruh repo) | Setiap baris JSONL valid, tidak ada file rusak |
| `data-eval` | `validate_dataset.py --strict` | Dataset utama 100% valid |
| `data-eval` | `split_dataset.py` | Split train/val berhasil & disjoint |
| `data-eval` | **drift check split** (`git diff`) | `train.jsonl`/`val.jsonl` sinkron dengan `samples.jsonl` |
| `data-eval` | validate train & val | Kedua split valid |
| `data-eval` | `format_chat.py --verify` | `*.chat.jsonl` sinkron dengan split sumber |
| `data-eval` | `format_chat.py --strict` | Token nyata (tokenizer Qwen) ≤ `max_seq_length` |
| `data-eval` | `run_eval.py --mode mock` | Eval dasar lulus (gate) |
| `data-eval` | upload artifact | `eval/report.json` + laporan token, 14 hari |

**Kontrol keamanan workflow:** `permissions: contents: read` (least privilege),
`concurrency` membatalkan run lama, action di-pin ke versi mayor (`@v4`/`@v5`),
dan tidak ada secret yang dipakai sehingga aman untuk PR dari fork.

**Drift check** mencegah `train.jsonl`/`val.jsonl` basi: bila `samples.jsonl`
diubah tanpa menjalankan ulang `split_dataset.py`, CI gagal dengan instruksi
perbaikan.

Jalankan seluruh pipeline secara lokal:

```bash
python -m compileall -q api data eval src tools
python data/validate_dataset.py --path data/samples.jsonl --strict --show-errors
python data/split_dataset.py
git diff --exit-code -- data/train.jsonl data/val.jsonl   # harus bersih
python data/format_chat.py --input data/train.jsonl --verify
python data/format_chat.py --input data/val.jsonl --verify
python data/format_chat.py --input data/train.jsonl --no-write --strict
python eval/run_eval.py --mode mock
```

---

## Training (saat GPU siap)

```bash
pip install -r requirements.txt   # termasuk torch, transformers, peft, trl, bitsandbytes

# Uji pipeline 3 step (dry-run)
python src/train_qlora.py --config configs/qlora_default.yaml --dry-run

# Training penuh
python src/train_qlora.py --config configs/qlora_default.yaml --dataset data/train.jsonl
```

Output adapter: `outputs/snrb-vanguard-7b-qlora/final_adapter/`

### Export ke GGUF

```bash
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp && cmake -B build && cmake --build build -j && cd ..

python src/export_gguf.py \
  --adapter-dir outputs/snrb-vanguard-7b-qlora/final_adapter \
  --quantize q4_k_m
```

### Jalankan dengan Ollama

```bash
cat > Modelfile <<'EOF'
FROM ./outputs/snrb-vanguard-7b-F16-Q4_K_M.gguf
PARAMETER temperature 0.2
PARAMETER num_ctx 4096
SYSTEM """
<isi prompts/system_persona.md>
"""
EOF
ollama create snrb-vanguard-7b -f Modelfile
ollama run snrb-vanguard-7b
```

---

## Environment Variables

| Variabel | Default | Keterangan |
|---|---|---|
| `INFERENCE_BASE_URL` | `http://127.0.0.1:11434` | Alamat backend (Ollama/llama-server/vLLM) |
| `MODEL_NAME` | `snrb-vanguard-7b` | Nama model di backend |
| `API_HOST` | `0.0.0.0` | Host API |
| `API_PORT` | `8000` | Port API |
| `REQUEST_TIMEOUT` | `120` | Timeout request ke backend (detik) |

---

## Prinsip Guardrail

- **Default-deny** untuk perintah berisiko & target di luar scope.
- **Allowlist** perintah read-only untuk analisis.
- **Scope wajib** sebelum pengujian aktif (rules of engagement tertulis).
- **Redaksi** kredensial/PII pada semua output.

Lihat `tools/guardrails.py` untuk implementasi dan `workflows/` untuk alur kerja.

---

## Keunggulan yang Diadopsi

Model ini mengadopsi **keunggulan** dari tiga keluarga model frontier — bukan
batasan/limitasi mereka:

| Sumber | Keunggulan yang diadopsi |
|---|---|
| **Claude** | Ringkas & jujur soal ketidakpastian, penalaran analitis, gaya natural |
| **Gemini** | Kesadaran multimodal (log/dokumen/gambar), konteks panjang, hemat biaya |
| **GPT** | Format terstruktur, tool-use yang disiplin, kepatuhan skema output |

Detail riset: [`docs/ai-models/`](docs/ai-models/README.md).

---

## Status

- [x] Struktur repository modular
- [x] Validator dataset + dataset **537 sampel**
- [x] Split train/val deterministik (`data/split_dataset.py`)
- [x] Chat template Qwen + cek `max_seq_length` (`data/format_chat.py`)
- [x] Konfigurasi & skrip QLoRA (dry-run ready)
- [x] Skrip export GGUF
- [x] API lokal OpenAI-compatible
- [x] Guardrails + workflows + skills
- [x] Eval harness dasar (mock & endpoint lokal)
- [x] CI GitHub Actions (sintaks, validasi, split, drift check, eval mock)
- [ ] Training penuh (butuh GPU)
- [ ] Evaluasi pada model hasil training

---

## Lisensi

Belum ditetapkan. Tambahkan `LICENSE` sebelum publikasi resmi.
