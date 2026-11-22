# Skill: Incident Response Playbook

Fungsi: Menyusun urutan tindakan defensif cepat saat terdeteksi anomali atau potensi insiden.

### Trigger
- Terdeteksi indikator anomali (brute force, data exfiltration, abnormal syscalls).
- Laporan user mengenai perilaku sistem yang mencurigakan.

### Input
- Deskripsi anomali/insiden.
- Dampak yang teramati.

### Aksi
1. Containment (Isolasi): Isolasi host atau akun terdampak untuk mencegah penyebaran.
2. Forensic Preservation: Ambil snapshot memori/log jika memungkinkan.
3. Remediation: Rotasi kredensial, sanitasi log/file, dan audit trail pemeriksaan.
4. Documentation: Catat urutan tindakan untuk analisis pasca-insiden.

### Guardrail
- Jangan pernah mengisolasi sistem kritikal tanpa persetujuan (kecuali dalam skenario simulasi resmi).
- Selalu utamakan integritas bukti (audit trail).

### Format Output
- Urutan langkah tindakan (Playbook).
- Prioritas tindakan (Critical -> Medium).
