# Riset Model AI: Claude, Gemini, ChatGPT (GPT)

Kumpulan catatan riset perbandingan tiga keluarga model AI frontier, disusun dari
**dokumentasi resmi vendor** (Anthropic, Google, OpenAI) pada **19 November 2026**.

## Daftar dokumen

| File | Isi |
|---|---|
| [00-perbandingan.md](00-perbandingan.md) | Perbandingan lintas vendor, keunggulan inti, matriks use case, pola multi-model |
| [01-claude-anthropic.md](01-claude-anthropic.md) | Profil & keunggulan Claude (Fable 5.2, Opus 5.5, Sonnet 5.5, Haiku 5.5) |
| [02-gemini-google.md](02-gemini-google.md) | Profil & keunggulan Gemini (4 Carbon/Neon/Hydrogen/Argon, 3.5 Flash-Lite) |
| [03-chatgpt-openai.md](03-chatgpt-openai.md) | Profil & keunggulan GPT (6.2 Astra/Sol, 6.1 Terra, 6 Luna, + model khusus) |

## TL;DR — keunggulan masing-masing

- **Claude (Anthropic)** — agentic coding & penalaran long-horizon terbaik, kejujuran tinggi,
  tulisan natural. Pilihan utama untuk agent berjalan lama, refactor besar, aplikasi akurasi-kritis.
- **Gemini (Google)** — multimodal paling luas (**teks, gambar, audio, video, PDF**) + context 1M +
  output hingga 1M + harga paling agresif. Pilihan utama untuk pipeline media & beban volume tinggi.
- **GPT (OpenAI)** — ekosistem platform terlengkap (Responses/Agents API, Codex, image, voice,
  embedding, moderation) + kontrol reasoning presisi + cached input termurah. Pilihan utama untuk
  membangun produk end-to-end multi-modalitas.

## Sumber

- Anthropic: `docs.anthropic.com` / `platform.claude.com/docs` (models overview, pricing, choosing a model)
- Google: `aistudio.google.com/docs` (models, choosing-a-model, pricing, latest-model)
- OpenAI: `platform.openai.com/docs` (models, model-selection, pricing, per-model pages)

> ⚠️ Nama model, harga, dan batas token berubah cepat. Verifikasi ulang ke sumber resmi sebelum
> memakainya untuk keputusan biaya atau arsitektur produksi.
