# Workflow: Defensive OSINT Report

**Tujuan:** menyusun laporan *attack surface* pasif dari **sumber terbuka** untuk
aset yang sah dimiliki/diizinkan, tanpa menyentuh sistem target.

**Batasan keras:**
- Hanya sumber publik & legal (Certificate Transparency, DNS publik, data terindeks).
- **Tidak** melakukan scanning aktif, brute-force, atau akses ke sistem target.
- **Tidak** mengumpulkan email pribadi / data privasi individu.
- Semua aktivitas dicatat untuk audit.

---

## Langkah

1. **Tetapkan scope**
   - Daftar domain/aset yang dimiliki atau diizinkan tertulis.
   - Konfirmasi: siapa pemilik, batas waktu, tujuan.

2. **Enumerasi subdomain pasif**
   - Certificate Transparency: `crt.sh`, Censys (data publik).
   - DNS publik: `dig`, `host`, record MX/TXT/NS.
   - Sumber: arsip publik, dokumentasi resmi.

3. **Pemetaan layanan publik**
   - Hanya metadata yang terlihat publik (judul halaman, header server).
   - Tanpa probe autentikasi, tanpa path fuzzing.

4. **Analisis paparan**
   | Temuan | Risiko | Rekomendasi |
   |---|---|---|
   | Subdomain staging terbuka | Data non-produksi bocor | Batasi akses / auth |
   | SPF/DKIM/DMARC lemah | Spoofing email | Perbaiki record DNS |
   | Versi software usang di header | Target CVE | Patch / sembunyikan versi |
   | Sertifikat hampir kedaluwarsa | Outage | Perbarui sertifikat |

5. **Korelasi & prioritas**
   - Urutkan berdasarkan dampak bisnis, bukan sekadar "menarik".

6. **Output**
   ```
   ## Ringkasan Eksekutif
   ## Scope & Metodologi (sumber terbuka, pasif)
   ## Aset Ditemukan
   ## Temuan & Risiko (tabel)
   ## Rekomendasi Berprioritas
   ## Lampiran: sumber data & timestamp
   ```

7. **Guardrail**
   - `guardrails.check_target()` wajib dipanggil dengan `allowed_scope` dari scope sah.
   - Redaksi email/kredensial sebelum publikasi.

---

## Yang ditolak

- Permintaan mencari "panel admin untuk dicoba masuk".
- Enumerasi email karyawan untuk kampanye phishing.
- Scanning aktif tanpa izin tertulis.
