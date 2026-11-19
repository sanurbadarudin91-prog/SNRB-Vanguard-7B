# Workflow: Code Audit (Defensif)

**Tujuan:** audit keamanan kode/konfigurasi milik pengguna, hasilkan temuan
berprioritas + perbaikan konkret.

**Prasyarat:** kode milik pengguna atau repo yang boleh diaudit. Tidak ada
pengujian aktif ke sistem pihak ketiga.

---

## Langkah

1. **Inventaris konteks**
   - Bahasa/framework, entry point, dependensi, dan area sensitif (auth, input, DB, file upload).
   - Catat versi dependency (`requirements.txt`, `package-lock.json`, dsb.).

2. **Secret scanning**
   - Cari kredensial hardcoded: API key, token, private key, password.
   - Redaksi temuan (jangan tampilkan nilai asli).

3. **Analisis pola risiko (OWASP-aligned)**
   | Kategori | Yang dicari |
   |---|---|
   | Injection | Query string-interpolated, `eval`, `exec`, shell command dari input |
   | AuthZ | Endpoint tanpa cek otorisasi, IDOR pada parameter ID |
   | AuthN | Password lemah, sesi tanpa expiry, JWT tanpa verifikasi |
   | Data exposure | `SELECT *`, debug mode, stack trace ke klien |
   | Deserialization | `pickle.loads`, `yaml.load` tanpa SafeLoader |
   | Dependency | CVE pada versi terpasang |

4. **Audit dependency**
   - Jalankan `pip-audit` / `npm audit` / `cargo audit`.
   - Tandai CVE kritikal & tinggi.

5. **Verifikasi**
   - Setiap temuan harus punya bukti (file:line + potongan kode).
   - Jangan menandai sebagai "confirmed" tanpa bukti.

6. **Output**
   ```
   ## Ringkasan
   <jumlah temuan per severity>

   ## Temuan
   ### [SEVERITY] <judul>
   - Lokasi: <file:line>
   - Bukti: <potongan kode, diredaksi>
   - Dampak: <...>
   - Perbaikan: <langkah konkret>
   ```

7. **Guardrail**
   - Gunakan `tools/guardrails.redact_secrets()` sebelum menampilkan output.
   - Jangan mengeksekusi kode target; analisis statis saja.

---

## Anti-pola yang harus dihindari

- Menyebut "vulnerable" tanpa bukti.
- Menyarankan menonaktifkan kontrol keamanan sebagai "fix".
- Menampilkan kredensial asli.
