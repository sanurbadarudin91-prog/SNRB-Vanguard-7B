# Perbandingan Claude vs Gemini vs GPT

> Disusun dari dokumentasi resmi Anthropic, Google, dan OpenAI (akses 2026-11-19).
> Fokus: keunggulan masing-masing + panduan memilih. Angka harga/spek bisa berubah.

## 1. Tabel cepat model flagship

| Aspek | Claude (Anthropic) | Gemini (Google) | GPT (OpenAI) |
|---|---|---|---|
| Model terkuat | Claude Fable 5.2 / Opus 5.5 | Gemini 4 Carbon | GPT-6.2 Astra |
| Model default umum | Claude Opus 5.5 | Gemini 4 Hydrogen | GPT-6.2 Sol |
| Model efisien | Claude Haiku 5.5 | Gemini 3.5 Flash-Lite | GPT-6 Luna |
| Context window | 1M (semua model) | 1M unified (+1M long decode) | 1.05M (max input 922K) |
| Max output | 128K | 64K default / 1M long-decode | 128K |
| Input multimodal | Teks + gambar | **Teks + gambar + audio + video + PDF** | Teks + gambar |
| Harga flagship (in/out per 1M) | $8 / $40 (Fable) · $4/$20 (Opus) | $2 / $10 (Carbon, intro) | $8 / $40 (Astra) |
| Harga default (in/out) | $4 / $20 (Opus 5.5) | $1.50 / $7.50 (Hydrogen) | $2 / $10 (Sol) |
| Kontrol reasoning | `effort` (low→max) + adaptive thinking | `thinking_level` (low→xhigh) | `reasoning_effort` (none→max) |
| Knowledge cutoff | Jun 2026 | (bervariasi; Carbon update Nov 2026) | Mei–Jun 2026 |
| Batch diskon | 50% | 50% | 50% |

## 2. Keunggulan inti masing-masing (one-liner)

- **Claude** → **agentic coding & penalaran long-horizon terbaik, kejujuran tinggi, tulisan
  natural.** Paling pas untuk agent yang berjalan lama, refactor besar, dan aplikasi yang
  menuntut akurasi serta respons manusiawi.
- **Gemini** → **multimodal paling luas (audio/video/PDF) + context 1M + harga paling agresif.**
  Paling pas untuk pipeline media, dokumen raksasa, dan beban volume tinggi yang sensitif biaya.
- **GPT** → **ekosistem platform terlengkap (Responses/Agents API, Codex, image, voice,
  embedding, moderation) + kontrol reasoning presisi + cached input termurah.**
  Paling pas untuk membangun produk end-to-end dengan banyak modalitas & tooling.

## 3. Kekuatan detail per dimensi

### 3.1 Coding & software engineering
1. **Claude** — paling kuat untuk agent coding otonom jangka panjang, refactor skala besar,
   multiturn berjam-jam (Claude Code, Opus 5.5).
2. **GPT** — Astra sangat kuat untuk proyek tersulit & planning; Sol jadi workhorse coding harian;
   Codex (CLI/IDE/Cloud) terintegrasi.
3. **Gemini** — Carbon/Neon kompetitif untuk multi-file debugging & arsitektur; harga lebih murah.

### 3.2 Multimodal
1. **Gemini** — menang jelas: audio, video, PDF native dalam satu model + long decode 1M.
2. **GPT** — teks + gambar di model utama; audio/gambar/video via model terpisah (realtime, image).
3. **Claude** — teks + gambar + vision kuat, tapi tanpa audio/video input.

### 3.3 Context & output panjang
- **Gemini**: 1M unified + output hingga 1M (long decode) → terbaik untuk output sangat panjang.
- **Claude & GPT**: 1M–1.05M input, output 128K.

### 3.4 Biaya
- **Termurah untuk kualitas tinggi**: Gemini (Carbon intro $2/$10; Hydrogen $1.50/$7.50).
- **Termurah untuk volume ekstrem**: GPT Luna ($0.10/$0.50) vs Gemini Flash-Lite ($0.30/$2.50)
  vs Claude Haiku ($0.10/$0.50, naik untuk prompt >100K).
- **Cached input termurah**: GPT (hingga 1/100 harga input).
- **Output mahal**: Claude Fable & GPT Astra ($40/1M).

### 3.5 Kontrol penalaran
- **Claude**: adaptive thinking + `effort` (low→max); tuning effort sering lebih baik dari ganti model.
- **Gemini**: `thinking_level` granular hingga `xhigh`; mudah pairing model per langkah.
- **GPT**: `reasoning_effort` eksplisit `none`→`max`; panduan task-per-effort sangat detail.

### 3.6 Ekosistem & tooling agent
1. **GPT** — Responses API, Agents SDK, Multi-agent beta, tool bawaan (web/file search, code
   interpreter, computer use, MCP, hosted shell) — paling lengkap.
2. **Gemini** — Search/Maps grounding, code execution, computer use, Managed Agents/Antigravity,
   model khusus (decision, image, video, live).
3. **Claude** — tool use + server tools (web search, code execution), MCP, deployment multi-cloud
   (Bedrock, Vertex, Foundry, AWS).

### 3.7 Kejujuran & akurasi fakta
- **Claude** — diposisikan unggul di honesty & menandai ketidakpastian.
- **Gemini** — Hydrogen menandai konteks hilang alih-alih menebak (klaim >5x lebih sedikit fabrikasi).
- **GPT** — kuat dengan reasoning effort tinggi + web search grounding.

### 3.8 Kualitas tulisan & UX chat
- **Claude** — respons paling natural/manusiawi; ideal customer-facing.
- **GPT Terra** — tulisan natural & jelas; ekosistem ChatGPT/Codex rapat.
- **Gemini** — baik, dengan integrasi Google Workspace/Search.

### 3.9 Deployment & kedaulatan data
- **Claude** — Claude API, Bedrock, Google Cloud (Vertex), Microsoft Foundry, Claude Platform on AWS;
  opsi data residency.
- **GPT** — Azure OpenAI, regional processing (+10%), EU data residency (beberapa model).
- **Gemini** — Google Cloud Vertex AI, region global/multi-region; integrasi GCP native.

### 3.10 Model khusus / domain
- **GPT** — Cyber (security), Rosalind (life sciences), Image, Realtime/Live voice, Transcribe,
  embedding, moderation, open-weight gpt-oss.
- **Gemini** — decision (klasifikasi), Nano Banana (image), Omni (video), Live (voice), TTS,
  Transcribe.
- **Claude** — fokus model general + Mythos (verified org, mis. cyber program); tidak banyak model
  spesialis terpisah.

## 4. Matriks pemilihan berdasarkan use case

| Use case | Pilihan utama | Alternatif kuat |
|---|---|---|
| Autonomous coding agent berjam-jam | Claude Opus 5.5 / Fable 5.2 | GPT-6.2 Astra, Gemini 4 Carbon |
| Coding harian / fitur di codebase | GPT-6.2 Sol | Claude Sonnet 5.5, Gemini 4 Hydrogen |
| Analisis video/audio/PDF panjang | **Gemini 4** (Carbon/Neon) | GPT (model audio/realtime terpisah) |
| Dokumen & output sangat panjang (≤1M) | **Gemini 4** (long decode) | Claude/GPT (output 128K) |
| Volume tinggi, biaya minimal | GPT-6 Luna / Gemini Flash-Lite | Claude Haiku 5.5 |
| Chatbot customer-facing natural | Claude Sonnet/Opus | GPT-6.1 Terra |
| Pipeline JSON ketat & tool calling | GPT (structured outputs) | Claude tool use, Gemini structured outputs |
| Riset kerentanan / security testing | GPT Cyber | Claude Mythos (verified), Gemini Carbon |
| Voice real-time / agent suara | GPT Realtime/Live | Gemini 3.8 Live |
| Image generation/editing | GPT-Image-2.6 | Gemini Nano Banana |
| Multi-agent orchestration | GPT (Agents SDK + Multi-agent) | Gemini pairing Carbon+Hydrogen |
| Data residency / on-prem | Claude (multi-cloud) / GPT (Azure, regional) | Gemini (Vertex regions), gpt-oss self-host |

## 5. Pola strategi multi-model (lintas vendor)

1. **Router per tugas** — kirim tugas ringan ke model murah (Luna/Flash-Lite/Haiku), tugas berat ke
   flagship (Astra/Opus/Carbon).
2. **Planner + Executor** — flagship untuk desain/diagnosis, model murah untuk implementasi massal
   (Gemini Carbon→Hydrogen; Claude advisor→executor; GPT Astra→Sol).
3. **Spesialis multimodal** — Gemini untuk audio/video/PDF, GPT untuk image/voice, Claude/GPT untuk kode.
4. **Cost guard** — manfaatkan cached input (GPT), Batch API 50% (semua), dan prompt caching (Claude/Gemini).
5. **Fallback & verifikasi** — pakai model kedua untuk cross-check output kritis (terutama fakta).

## 6. Ringkasan eksekutif

- **Butuh agent coding paling otonom & jujur?** → **Claude**.
- **Butuh multimodal (video/audio/PDF) + murah + context/output raksasa?** → **Gemini**.
- **Butuh platform produk lengkap (API, Codex, image, voice, embedding) & kontrol reasoning presisi?** → **GPT**.

Ketiganya kelas frontier dan saling mendekat; keputusan akhir sebaiknya berbasis **evaluasi pada
prompt & data sendiri**, bukan hanya benchmark publik.
