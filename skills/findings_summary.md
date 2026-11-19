# Skill: Technical Findings Summary

**Kapan dipakai:** setelah analisis (log, kode, arsitektur, insiden) selesai dan
hasilnya perlu diringkas untuk pembaca teknis maupun non-teknis.

**Tujuan:** menyajikan temuan secara terstruktur — apa yang ditemukan, seberapa
serius, buktinya apa, dan apa yang harus dilakukan — tanpa melebih-lebihkan.

---

## Prosedur

### 1. Kumpulkan temuan mentah
Setiap temuan **wajib** punya:
- Bukti (file:line, event ID, output perintah, potongan log).
- Lokasi/aset terdampak.
- Tingkat keyakinan: `confirmed` / `likely` / `suspected`.

Temuan tanpa bukti → tulis di bagian "Belum Terverifikasi", bukan di temuan utama.

### 2. Tetapkan severity
| Severity | Kriteria |
|---|---|
| Critical | Dampak langsung ke data sensitif / layanan publik / ada eksploitasi aktif |
| High | Kompromi terkonfirmasi atau kelemahan yang mudah dieksploitasi |
| Medium | Kelemahan nyata tapi butuh kondisi tambahan |
| Low | Hardening / best practice, dampak minimal |
| Info | Observasi, bukan kelemahan |

Sertakan alasan singkat penetapan severity — bukan hanya label.

### 3. Redaksi
Sebelum menulis laporan:
- Ganti kredensial/token dengan `<REDACTED>`.
- Masking email/PII (`<EMAIL_REDACTED>`, `203.0.113.x`).
- Jangan sertakan payload yang bisa langsung dipakai menyerang.

Gunakan `tools/guardrails.redact_secrets()` bila tersedia.

### 4. Susun ringkasan
Urutan yang disarankan:
1. **Ringkasan eksekutif** — 3–5 kalimat: apa, seberapa serius, dampak bisnis.
2. **Temuan berprioritas** — tabel severity → judul → aset.
3. **Detail per temuan** — bukti, dampak, perbaikan.
4. **Rekomendasi berurutan** — apa dulu, kenapa.
5. **Belum terverifikasi** — hal yang butuh data tambahan.

### 5. Nyatakan ketidakpastian
- "Terdapat indikasi X; belum bisa dipastikan tanpa Y."
- Jangan menulis "terbukti" bila hanya ada korelasi.

### 6. Tutup dengan aksi
Setiap temuan harus punya minimal satu aksi konkret dengan pemilik/jangka waktu
bila memungkinkan.

---

## Format Output

```
## Ringkasan Eksekutif
<3-5 kalimat: temuan utama, severity tertinggi, dampak>

## Tabel Temuan
| # | Severity | Temuan | Aset | Keyakinan |
|---|---|---|---|---|

## Detail
### 1. [HIGH] <judul>
- Bukti: <file:line / event / output, diredaksi>
- Dampak: <...>
- Perbaikan: <langkah konkret>

## Rekomendasi Berurutan
1. <aksi> — <alasan prioritas>
2. ...

## Belum Terverifikasi
- <hal yang butuh data tambahan>

## Metodologi & Batasan
- Sumber data: ...
- Tidak dilakukan: <mis. tidak ada scanning aktif>
```

---

## Larangan

- Jangan menaikkan severity untuk menakut-nakuti.
- Jangan menurunkan severity karena "sulit diperbaiki".
- Jangan menampilkan kredensial atau PII mentah.
- Jangan menyimpulkan kompromi tanpa bukti akses sukses.
- Jangan menghapus temuan "belum terverifikasi" — justru itu informasi penting.
