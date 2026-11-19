# SNRB-Vanguard-7B

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
├── data/
│   ├── samples.jsonl         # dataset utama (73 sampel, format messages)
│   ├── train.jsonl           # split training (dihasilkan split_dataset.py)
│   ├── val.jsonl             # split validasi (dihasilkan split_dataset.py)
│   ├── validate_dataset.py   # validator JSONL + statistik token
│   └── split_dataset.py      # pembagi train/val deterministik (seeded)
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
pip install fastapi uvicorn pydantic pyyaml requests

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

`data/samples.jsonl` berisi **73 contoh** percakapan format `messages`
(`system` → `user` → `assistant`) yang konsisten dengan persona:
analisis log/kode, hardening, triase insiden, arsitektur sistem, dan OSINT legal.

| Metrik | Nilai |
|---|---|
| Total sampel | 73 |
| Total karakter | ~70.062 |
| Estimasi token | ~17.490 (~239/sampel) |
| Panjang token min/max | 161 / 284 |

**Pembagian train/val** (deterministik, `--seed 42`, `--val-ratio 0.2`):

```bash
python data/split_dataset.py            # -> data/train.jsonl (58) + data/val.jsonl (15)
python data/split_dataset.py --val-ratio 0.15 --seed 7
python data/split_dataset.py --no-validate
```

Skrip ini menjamin **tidak ada kebocoran id** antara train & val (dicek
otomatis), lalu memanggil `validate_dataset.py` pada kedua file.

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
- [x] Validator dataset + dataset 73 sampel
- [x] Split train/val deterministik (`data/split_dataset.py`)
- [x] Konfigurasi & skrip QLoRA (dry-run ready)
- [x] Skrip export GGUF
- [x] API lokal OpenAI-compatible
- [x] Guardrails + workflows + skills
- [x] Eval harness dasar (mock & endpoint lokal)
- [ ] Training penuh (butuh GPU)
- [ ] Evaluasi pada model hasil training

---

## Lisensi

Belum ditetapkan. Tambahkan `LICENSE` sebelum publikasi resmi.
