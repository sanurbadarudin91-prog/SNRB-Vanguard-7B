# ChatGPT / GPT (OpenAI) — Profil & Keunggulan

> Sumber: dokumentasi resmi OpenAI (platform.openai.com/docs), diakses 2026-11-19.
> Angka dapat berubah; verifikasi ulang sebelum dipakai untuk keputusan biaya/arsitektur.

## Ringkasan

GPT adalah keluarga model OpenAI dengan ekosistem **platform paling lengkap**: model teks &
reasoning, image, audio/realtime voice, embedding, moderation, computer use, serta tooling
agentik (Responses API, Agents SDK, Codex). Model flagship saat ini **GPT-6.2 Astra**.

## Lineup saat ini (generasi GPT-6.2 / 6.1 / 6)

| Model | Peran | Harga (in / out per 1M) | Context | Max output | Knowledge cutoff |
|---|---|---|---|---|---|
| **GPT-6.2 Astra** (`gpt-6.2-astra`) | Paling kapabel untuk proyek tersulit end-to-end (engineering, analisis, planning) | $8 / $40 | 1.05M (max input 922K) | 128K | Mei 2026 |
| **GPT-6.2 Sol** (`gpt-6.2-sol`) | Model andalan harian: coding, agent skala besar — **default rekomendasi** | $2 / $10 | 1.05M (max input 922K) | 128K | Jun 2026 |
| **GPT-6.1 Terra** (`gpt-6.1-terra`) | Visual reasoning, computer use presisi, tulisan natural & cepat | $1 / $5 | 1.05M (max input 922K) | 128K | Jun 2026 |
| **GPT-6 Luna** (`gpt-6-luna`) | Paling efisien untuk tugas terfokus volume tinggi | $0.10 / $0.50 | 1.05M (max input 922K) | 128K | Mei 2026 |

Model khusus / lain:
- **GPT-6.2 / 6.1 Sol, 5.x series** (5.2 Pro, 5.4, 5.5, 5.6 Sol/Terra/Luna, dst.) — generasi sebelumnya, masih tersedia.
- **GPT-5.6 / GPT-6 Cyber** — model keamanan siber untuk riset kerentanan & security testing
  terotorisasi (mis. `gpt-5.6-cyber`: 400K context, $12.5/$75).
- **GPT-Image-2.6 Flare / Sunburst** — generasi & edit gambar.
- **GPT-Live-1, GPT-Realtime-2.1, GPT-Transcribe, GPT-Audio-1.5** — voice/realtime/audio.
- **gpt-oss-120b / gpt-oss-20b** — open-weight (120b muat di satu H100).
- **text-embedding-3-large/small**, **omni-moderation** — embedding & moderasi.
- **GPT-Rosalind** — reasoning life-sciences untuk organisasi terverifikasi.

Catatan pricing:
- **Cached input** sangat murah: Astra $0.40, Sol $0.10, Terra $0.05, Luna $0.01 per 1M.
- **Batch & Flex** = 50% harga standar; **Fast mode** = 2x; **Ultrafast** 3x (s/d Feb 2027, lalu 6x).
- Request > 272K input token: input & cache 2x, output 1.5x untuk seluruh request.
- **Regional processing** +10% premium.

## Keunggulan utama GPT / OpenAI

1. **Ekosistem platform terlengkap** — satu vendor untuk teks, reasoning, image gen,
   realtime voice, transcription, embedding, moderation, dan computer use.
2. **Responses API + Agents SDK + Multi-agent beta** — infrastruktur agent paling matang
   (delegasi subagent, background mode, WebSocket streaming, mid-turn steering, webhooks).
3. **Kontrol reasoning effort eksplisit** (`none`→`max`) — tuning presisi antara kualitas,
   latensi, dan biaya per request.
4. **Tool bawaan kaya** — web search, file search, image generation, code interpreter,
   hosted shell, apply_patch, computer use, MCP, tool search.
5. **Structured outputs & function calling** yang sangat andal → cocok untuk pipeline produksi
   yang butuh JSON ketat / integrasi tool.
6. **Cached input termurah di kelasnya** (hingga 1/100 harga input) → sangat hemat untuk
   system prompt panjang berulang.
7. **Jalur produk konsumen ↔ API rapat** — ChatGPT, Codex (CLI/IDE/Cloud), dan API berbagi
   model & perilaku, memudahkan transisi prototipe → produksi.
8. **Model khusus domain** — Cyber (security), Rosalind (life sciences), image, audio, realtime.
9. **Open-weight tersedia** (gpt-oss) → opsi self-host/on-prem untuk 120b/20b.
10. **Codex sebagai coding agent** — CLI, IDE extension, cloud, GitHub Action, SDK.

## Kapan memilih GPT

| Kebutuhan | Mulai dari |
|---|---|
| Proyek tersulit: planning kompleks, engineering berat, analisis mendalam | Astra (medium→extra high) |
| Default sehari-hari: bug fix, fitur di codebase, draft dokumen, agent produksi | Sol (medium) |
| Interpretasi visual (chart, screenshot), computer use, tulisan natural | Terra |
| Tugas kecil berulang, ekstraksi field, otomasi volume tinggi | Luna |
| Riset kerentanan / security testing terotorisasi | GPT Cyber |
| Voice/realtime, image gen, embedding, moderasi | Model khusus terkait |

## Panduan reasoning effort (dari OpenAI)

- **Luna · Low** — edit file kecil, ekstraksi field dengan hasil jelas.
- **Luna · Extra high** — cari update antar-app, prioritas follow-up, problem berbatas jelas.
- **Terra · Medium** — navigasi desktop app, update record, fix terverifikasi.
- **Sol · Medium** — fix bug & tambah fitur di codebase, draft dokumen.
- **Sol · Extra high** — tugas multistep yang butuh testing & revisi bertahap.
- **Astra · Low** — eksekusi brief jelas jadi output siap pakai.
- **Astra · Medium** — rencanakan & jalankan proyek kompleks, adaptasi saat info baru masuk.
- **Astra · Extra high** — problem open-ended, timbang trade-off, uji asumsi.

## Keterbatasan / catatan

- Model teks flagship **tidak mendukung audio/video sebagai input** (hanya teks + gambar);
  media ditangani model terpisah (realtime/audio/image).
- Astra/Sol **menolak** `reasoning_effort: none`.
- Harga tier Astra tinggi ($40/1M output) — pakai untuk kasus yang benar-benar sulit.
- Lini model cepat berubah (banyak seri 5.x/6.x) — perlu cek katalog saat implementasi.
