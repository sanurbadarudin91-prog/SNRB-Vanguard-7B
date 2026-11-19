# Skill: Log Triage

**Kapan dipakai:** ada lonjakan event anomali di log (auth, web, firewall, EDR)
yang butuh klasifikasi cepat & langkah defensif.

**Input:** file log atau potongan log, plus konteks (sistem, periode, baseline).

---

## Prosedur

### 1. Normalisasi
- Identifikasi format: syslog, JSON, Apache/Nginx combined, Windows Event, CEF.
- Parse ke field: `timestamp`, `source_ip`, `user`, `event`, `status`.

### 2. Baseline
- Bandingkan dengan periode normal (7–30 hari).
- Hitung lonjakan: event/detik, jumlah IP unik, jumlah akun unik.

### 3. Klasifikasi pola
| Pola | Indikator | Kategori |
|---|---|---|
| Banyak gagal login, 1 akun | `Failed password` berulang | Brute force |
| Banyak akun, 1 IP | `4625` lintas user | Password spraying |
| 1 IP, banyak path 404 | Path fuzzing | Reconnaissance |
| Payload aneh di query | `'`, `UNION`, `<script>` | Injection attempt |
| Login sukses setelah gagal | 4625 → 4624 dari IP sama | Kemungkinan kompromi |

### 4. Korelasi
- Kaitkan source IP dengan event lain (port scan → login → akses data).
- Cek apakah ada akun/IP yang juga muncul di alert lain.

### 5. Keputusan triage
```
Ringkasan   : <1-2 kalimat>
Severity    : low | medium | high | critical
Bukti       : <event + count + time range>
Hipotesis   : <apa yang mungkin terjadi>
Langkah     : 1. <aksi defensif> ...
Eskalasi    : <ya/tidak + alasan>
```

### 6. Rekomendasi defensif (pilih yang relevan)
- Rate-limit / blokir source IP.
- Paksa reset kredensial & cabut sesi (jika ada login sukses).
- Aktifkan MFA pada akun terdampak.
- Tambah detection rule untuk pola tersebut.

---

## Aturan
- **Jangan** mengubah file log asli; bekerja pada salinan.
- Redaksi IP internal/PII saat berbagi laporan keluar.
- Jangan menyimpulkan "kompromi" tanpa bukti login sukses atau aktivitas pasca-akses.
