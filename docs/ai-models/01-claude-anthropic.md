# Claude (Anthropic) — Profil & Keunggulan

> Sumber: dokumentasi resmi Anthropic (platform.claude.com / docs.anthropic.com), diakses 2026-11-19.
> Angka dapat berubah; verifikasi ulang sebelum dipakai untuk keputusan biaya/arsitektur.

## Ringkasan

Claude adalah keluarga LLM frontier dari Anthropic yang dikenal paling kuat di
**agentic coding, penalaran panjang (long-horizon), kejujuran/rendah halusinasi, dan gaya
respons yang natural/manusiawi**. Semua model generasi 5.x mendukung input teks + gambar,
output teks, multibahasa, vision, dan tool use.

## Lineup saat ini (generasi 5.5 / 5.2)

| Model | Peran | Latency | Harga (in / out per 1M) | Thinking | Context | Max output |
|---|---|---|---|---|---|---|
| **Claude Fable 5.2** (`claude-fable-5-2`) | Penalaran berat & kerja agentic long-horizon | Moderate | $8 / $40 | Adaptive (selalu aktif) | 1M | 128K |
| **Claude Opus 5.5** (`claude-opus-5-5`) | Agentic coding & knowledge work jangka panjang — **default paling aman** | Moderate | $4 / $20 | Adaptive (selalu aktif) | 1M | 128K |
| **Claude Sonnet 5.5** (`claude-sonnet-5-5`) | Kombinasi terbaik kecepatan + kecerdasan | Fast | $2 / $10 | Adaptive | 1M | 128K |
| **Claude Haiku 5.5** (`claude-haiku-5-5`) | Volume tinggi & latensi rendah (klasifikasi, ekstraksi, routing) | Fastest | dari $0.10 / $0.50 | Adaptive | 1M | 128K |

Catatan:
- **Mythos 5.2** = kapabilitas sama dengan Fable 5.2, tapi hanya untuk organisasi
  terverifikasi (mis. Cyber Verification Program).
- Generasi lama (Opus 4.x, Sonnet 4.x, Haiku 4.5) masih tersedia tapi bukan default.
- **Pricing tambahan:** Batch API diskon 50%; cache read 0.1x harga input (0.025x di Fable 5.2,
  0.05x di Opus 5.5 & Sonnet 5.5); cache write 5 menit = 1.25x, 1 jam = 2x.
- **Fast mode** (Fable 5.2, Opus 5.5, Opus 5, Opus 4.8): output hingga 2.5x lebih cepat
  dengan harga premium.
- **Haiku 5.5** bertarif lebih tinggi untuk prompt > 100K token.
- Semua model 4.6+ mendapat context window 1M penuh dengan harga standar (tanpa premi long-context).
- Knowledge/training cutoff: **Juni 2026**.
- Retensi minimal: Fable 5.2 s/d Nov 2027, Opus 5.5 s/d Sep 2027, Sonnet 5.5 s/d Sep 2027,
  Haiku 5.5 s/d Okt 2027.

## Keunggulan utama Claude

1. **Agentic coding kelas teratas** — tulang punggung produk coding agent (Claude Code),
   kuat untuk refactor skala besar, kerja multiturn/berjam-jam, dan eksekusi tool yang andal.
2. **Penalaran long-horizon** — Fable 5.2 dirancang untuk sesi agent yang berjalan berjam-jam,
   riset mendalam bertahap, sampai output jadi (dokumen/spreadsheet/deck).
3. **Adaptive thinking + parameter `effort`** — satu model bisa "diatur" kecerdasan vs
   latensi/biaya lewat effort (`low`→`max`); sering lebih efektif daripada ganti model.
4. **Kejujuran & rendah halusinasi** — diposisikan kuat di honesty dan menolak/menandai
   ketidakpastian; cocok untuk domain yang sensitif terhadap akurasi.
5. **Kualitas tulisan natural** — respons kaya, mirip manusia; ideal untuk aplikasi
   customer-facing/chat. (Bisa dibuat lebih ringkas lewat prompting.)
6. **Context 1M + output 128K** di semua model current, dengan harga flat (tanpa premi).
7. **Multibahasa & vision kuat**, termasuk pemrosesan gambar/dokumen.
8. **Prompt caching & Batch API** — penghematan besar untuk system prompt panjang / volume besar.
9. **Ekosistem deployment luas** — Claude API, Amazon Bedrock, Google Cloud (Vertex),
   Microsoft Foundry, Claude Platform on AWS.
10. **Strategi multi-model** — pola "executor + advisor" (eskalasi ke model mahal saat sulit)
    dan "orchestrator + worker" (delegasi massal ke model murah).

## Kapan memilih Claude

| Kebutuhan | Mulai dari |
|---|---|
| Kapabilitas tertinggi / agent berjam-jam / deep research | Fable 5.2 |
| Agentic coding & enterprise kompleks (default umum) | Opus 5.5 |
| Sehari-hari: coding, agent, analisis data, konten | Sonnet 5.5 |
| Latensi & biaya paling rendah, volume tinggi, subagent | Haiku 5.5 |

## Pola pemilihan model (dari Anthropic)

- **Efficiency-first:** mulai dari Haiku 5.5 → uji → naikkan hanya jika ada gap kapabilitas.
- **Capability-first:** mulai dari Opus 5.5 → optimalkan prompt → turunkan effort/model.
- Naik ke Fable 5.2 hanya jika evaluasi di `xhigh`/`max` effort masih kurang.

## Keterbatasan / catatan

- Latensi "moderate" di model teratas — kurang ideal untuk target sub-detik.
- Harga output relatif tinggi di tier Fable ($40/1M).
- Fitur tertentu (fast mode, computer use versi baru) punya breaking change antar versi —
  baca panduan migrasi saat berpindah model.
