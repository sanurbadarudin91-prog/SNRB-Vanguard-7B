# Skill: Log Secret Scrubber

Fungsi: Menyensor data sensitif (API key, token, kredensial, PII) pada log atau output sistem sebelum ditampilkan atau disimpan.

### Trigger
- Terdeteksi adanya output yang berisi pola string yang menyerupai secret (regex patterns).
- Kebutuhan untuk logging output sistem ke penyimpanan eksternal.

### Input
- Teks output mentah (raw log/text).
- Daftar pola sensitif (API Key, JWT token, PII).

### Aksi
1. Identifikasi string dengan regex pattern yang sudah ditentukan (`/[a-zA-Z0-9]{32,}/`, `Bearer [a-zA-Z0-9\._\-]+`, dll).
2. Ganti string tersebut dengan `[REDACTED_SECRET]`.
3. Validasi bahwa tidak ada bagian krusial dari log (seperti timestamp atau status error) yang ikut terhapus.

### Guardrail
- Jangan pernah menyimpan data asli di memori melebihi durasi proses scrubbing.
- Pastikan algoritma scrubbing efisien (hindari *ReDoS* pada regex).

### Format Output
- String bersih (scrubbed) yang aman untuk ditampilkan atau disimpan.
