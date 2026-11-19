# Skill: Staged Planning

**Kapan dipakai:** permintaan kompleks atau multi-langkah (audit, migrasi,
investigasi, desain arsitektur) yang butuh rencana bertahap sebelum eksekusi.

**Tujuan:** mengubah permintaan besar menjadi rencana bertahap yang bisa
diverifikasi, tanpa melanggar batas defensif & legal.

---

## Prosedur

### 1. Klarifikasi tujuan
Tulis satu kalimat tujuan yang terukur.
- Buruk: "amankan server"
- Baik: "tutup akses SSH password-based di 3 host produksi tanpa downtime"

### 2. Tetapkan batas
Sebelum menyusun langkah, jawab:
- Aset siapa? (milik pengguna / ada izin tertulis?)
- Apakah ada tindakan aktif ke sistem lain? (jika ya → butuh scope)
- Apa yang **tidak** boleh dilakukan? (data destruktif, downtime, biaya)

Jika batas tidak jelas → **berhenti dan tanya**, jangan berasumsi.

### 3. Pecah menjadi fase
Format standar:
```
Fase 0 — Persiapan   : inventaris, akses, backup, baseline
Fase 1 — Pengamanan  : langkah berisiko rendah, reversibel
Fase 2 — Perubahan   : perubahan inti, satu per satu
Fase 3 — Verifikasi  : uji fungsi & keamanan
Fase 4 — Rollback    : rencana bila gagal (wajib ada)
```

### 4. Setiap langkah harus punya
| Elemen | Contoh |
|---|---|
| Aksi | "Set `PermitRootLogin no` di sshd_config" |
| Bukti keberhasilan | "`sshd -t` lolos, login root ditolak" |
| Risiko | "Bisa mengunci diri sendiri" |
| Mitigasi | "Buka sesi kedua sebelum menutup yang lama" |
| Reversibel? | "Ya — kembalikan baris konfigurasi" |

### 5. Urutkan berdasarkan risiko
- Reversibel & berdampak kecil → lebih dulu.
- Ireversibel / berdampak luas → terakhir, setelah verifikasi.

### 6. Tentukan titik berhenti
Cantumkan kondisi kapan rencana harus **dihentikan** dan dieskalasi:
- Anomali tak terduga pada verifikasi.
- Dampak di luar perkiraan.
- Bukti bahwa asumsi awal salah.

---

## Format Output

```
## Tujuan
<satu kalimat terukur>

## Batas & Asumsi
- Aset: ...
- Izin: ...
- Tidak boleh: ...

## Rencana Bertahap
### Fase 0 — Persiapan
1. <aksi> → bukti: <...> | risiko: <...> | rollback: <...>
...

## Titik Berhenti
- Jika <kondisi>, hentikan dan eskalasi.

## Verifikasi Akhir
- <kriteria sukses yang bisa diuji>
```

---

## Larangan

- Jangan menyusun langkah yang menyerang sistem pihak ketiga tanpa izin.
- Jangan menyembunyikan langkah berisiko di antara langkah aman.
- Jangan memberi rencana tanpa rollback untuk perubahan ireversibel.
- Jangan menandai fase "selesai" tanpa bukti verifikasi.
