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
│   ├── samples.jsonl         # dataset contoh (format messages)
│   └── validate_dataset.py   # validator JSONL + statistik token
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
├── workflows/
│   ├── code_audit.md
│   └── defensive_osint_report.md
├── skills/
│   ├── log_triage.md
│   └── prompt_adapter.md
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

# 3. Cek guardrails (demo)
python tools/guardrails.py

# 4. Jalankan API (butuh backend inference lokal, mis. Ollama)
export INFERENCE_BASE_URL=http://127.0.0.1:11434
export MODEL_NAME=snrb-vanguard-7b
uvicorn api.server:app --host 0.0.0.0 --port 8000

# 5. Tes API
python api/test_infer.py --base-url http://127.0.0.1:8000
```

---

## Training (saat GPU siap)

```bash
pip install -r requirements.txt   # termasuk torch, transformers, peft, trl, bitsandbytes

# Uji pipeline 3 step (dry-run)
python src/train_qlora.py --config configs/qlora_default.yaml --dry-run

# Training penuh
python src/train_qlora.py --config configs/qlora_default.yaml --dataset data/samples.jsonl
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
- [x] Validator dataset + dataset contoh
- [x] Konfigurasi & skrip QLoRA (dry-run ready)
- [x] Skrip export GGUF
- [x] API lokal OpenAI-compatible
- [x] Guardrails + workflows + skills
- [ ] Training penuh (butuh GPU)
- [ ] Evaluasi pada dataset uji internal

---

## Lisensi

Belum ditetapkan. Tambahkan `LICENSE` sebelum publikasi resmi.
