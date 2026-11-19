# Gemini (Google) — Profil & Keunggulan

> Sumber: dokumentasi resmi Google AI (aistudio.google.com/docs, ai.google.dev), diakses 2026-11-19.
> Angka dapat berubah; verifikasi ulang sebelum dipakai untuk keputusan biaya/arsitektur.

## Ringkasan

Gemini adalah keluarga model **natively multimodal** dari Google DeepMind. Semua model
general-purpose menerima **teks, gambar, audio, video, dan PDF** dalam satu API, dengan
context window 1M token dan integrasi kuat ke ekosistem Google (Search grounding, Maps,
code execution, computer use).

## Lineup saat ini (generasi Gemini 4 + Flash-Lite)

| Model | Peran | Kecepatan | Harga (in / out per 1M) | Thinking level | Context | Max output |
|---|---|---|---|---|---|---|
| **Gemini 4 Carbon** (`gemini-4-carbon`) | Model penalaran terkuat: software engineering kompleks, sains/matematika, akurasi fakta, agent multi-step | Deliberate | $2 / $10 (intro s/d 30 Nov 2026; lalu $4 / $20) | low, medium (default), high | 1M unified | 64K default / 1M long-decode |
| **Gemini 4 Neon** (`gemini-4-neon`) | Frontier cepat: multi-file coding, knowledge work, sains | Moderate | $3 / $15 | low, medium, high (default), xhigh | 1M unified | 64K / 1M |
| **Gemini 4 Hydrogen** (`gemini-4-hydrogen`) | Default umum: coding harian, app interaktif, agent pakai tool, dokumen multimodal | Fast | $1.50 / $7.50 | low, medium, high (default), xhigh | 1M unified | 64K / 1M |
| **Gemini 3.5 Flash-Lite** (`gemini-3.5-flash-lite`) | Volume tinggi & biaya terendah: ekstraksi, terjemahan, ringkasan, target sub-detik | Fastest | $0.30 / $2.50 | minimal (default), low, medium, high | 1M input | 64K |
| **Gemini 4 Argon** (`gemini-4-argon`) | Penalaran frontier efisien (token lebih hemat dari Carbon) | — | $2 / $10 (intro, sama seperti Carbon) | — | 1M | 64K / 1M |

Catatan:
- **Free tier:** Hydrogen & Flash-Lite tersedia gratis; **Carbon, Neon, Argon tidak**.
- **Batch / Flex** = 50% harga standar; **Priority** = ~1.8x harga standar.
- **Carbon & Argon**: implicit caching saja (explicit caching tidak didukung); cache $0.10/1M.
- **Grounding Google Search**: 5.000 request gratis/bulan (shared antar model Gemini 3+),
  lalu $14/1.000 request (cap 1.500/hari). Maps grounding juga tersedia.
- Update terakhir Carbon: **November 2026**.

## Keunggulan utama Gemini

1. **Natively multimodal (paling luas)** — teks, gambar, **audio, video, PDF** dalam satu
   model/API. Ini pembeda terbesar vs Claude/GPT yang input-nya teks + gambar.
2. **Context 1M + long decode 1M** — window input & output besar dalam satu model; cocok untuk
   video panjang, basis kode besar, dan dokumen raksasa.
3. **Harga agresif** — tier unggulan sangat murah dibanding kompetitor (Carbon $2/$10 intro),
   Flash-Lite $0.30/$2.50 untuk volume tinggi.
4. **Integrasi ekosistem Google** — Search grounding (data real-time), Maps grounding,
   code execution, file search, URL context — semua built-in.
5. **Pilihan thinking level granular** (hingga `xhigh`) → kontrol latensi vs kedalaman penalaran.
6. **Akurasi fakta & anti-halusinasi** — Hydrogen diklaim memangkas klaim fabrikasi >5x vs
   Gemini 3.8 Flash dengan menandai konteks yang hilang alih-alih menebak.
7. **Pola pairing model** — Carbon untuk diagnosis/desain, Hydrogen untuk implementasi & subagent
   paralel (schema request identik, mudah di-route per langkah).
8. **Model khusus (specialized)** — `gemini-decision-1` (klasifikasi/routing tanpa output token),
   Nano Banana (gambar), Gemini Omni (video), Gemini Live (voice real-time), TTS, Transcribe.
9. **Video/audio generation & understanding** — kemampuan media yang tidak dimiliki kompetitor
   di tingkat API yang sama.

## Kapan memilih Gemini

| Kebutuhan | Mulai dari |
|---|---|
| Problem tersulit: arsitektur sistem, debugging multi-file, sains, security audit | Carbon |
| Coding/knowledge work kompleks frekuensi tinggi, tapi lebih cepat dari Carbon | Neon |
| Default proyek baru: coding harian, app interaktif, agent multimodal | Hydrogen |
| Volume tinggi, biaya minimal, latensi sub-detik | Flash-Lite |
| Klasifikasi/routing/moderation murni (label/yes-no/score) | `gemini-decision-1` |
| Gambar / video / voice real-time | Nano Banana / Omni / Live |

## Keterbatasan / catatan

- Tier teratas (Carbon/Neon/Argon) tidak ada di free tier.
- Carbon/Argon hanya implicit caching (tidak bisa explicit cache breakpoint).
- Nama model & harga sedang dalam masa transisi (intro pricing berakhir 1 Des 2026).
- Flash-Lite punya window input 1M tapi output terpisah 64K (bukan unified 1M).
