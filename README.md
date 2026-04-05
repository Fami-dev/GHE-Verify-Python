# GHE Verify Python

## Apa itu GitHub Education Verify?

GitHub Education Verify adalah proses untuk mengajukan status pelajar atau pengajar agar akun GitHub bisa mendapatkan akses GitHub Education benefits.

Project ini membantu mengelola proses tersebut lewat bot Telegram dan backend API, termasuk alur data pengguna, generate dokumen pendukung, dan monitoring status pengajuan.

## Fitur

- Verifikasi Student dan Teacher
- Bot Telegram untuk alur pengguna dan owner/admin
- API backend untuk integrasi web
- Sistem kredit (referral, check-in harian, top up)
- Konfigurasi multi-sekolah
- Logging dan penyimpanan status verifikasi

## Requirements

- Python 3.10 atau lebih baru
- Akun Telegram API (API_ID, API_HASH, BOT_TOKEN)
- Dependensi Python di [requirements.txt](requirements.txt)

## Tata Cara Penginstalan

1. Clone repository ini.
2. Masuk ke folder project.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Buat file konfigurasi `.env`:

```bash
# Linux/macOS (buat .env dari template)
cp .env.example .env

# Windows PowerShell (buat .env dari template)
Copy-Item .env.example .env
```

5. Isi nilai penting di file .env:

- BOT_TOKEN
- API_ID
- API_HASH
- OWNER_ID
- API_SECRET

6. Jalankan semua service sekaligus (disarankan):

```bash
python run_all.py
```

Atau jalankan manual satu per satu:

7. Jalankan bot:

```bash
python bot.py
```

8. Jalankan API server:

```bash
python api_server.py
```

## Catatan

- Jangan upload file .env ke GitHub.
- Simpan session Telegram dengan aman.
- Gunakan API_SECRET yang kuat untuk production.