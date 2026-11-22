# Skill: Code Hardening Audit

Fungsi: Memeriksa celah keamanan umum pada kode/API dan menyarankan perbaikan teknis.

### Trigger
- User mengirimkan potongan kode untuk dianalisis.
- Permintaan audit keamanan pada endpoint API baru.

### Input
- Snippet kode (source code).
- Tipe aplikasi (web, API, script sistem).

### Aksi
1. Scan untuk celah OWASP (Injeksi, Broken Auth, dll).
2. Periksa penanganan error (apakah detail error bocor ke user?).
3. Periksa input validation dan sanitization (apakah input langsung dipakai?).
4. Periksa eksposur data sensitif (apakah ada hardcoded secret?).

### Guardrail
- Hanya berikan saran perbaikan, jangan menjalankan kode audit dalam lingkungan produksi.
- Fokus pada *static analysis* (tidak melakukan scanning aktif pada sistem live).

### Format Output
- Daftar temuan (Kritis/High/Medium/Low).
- Penjelasan teknis singkat tentang celah.
- Contoh perbaikan (remediasi) konkret.
