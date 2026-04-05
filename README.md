<div align="center">

# GHE Verify Python

Bot Telegram + API backend untuk membantu alur verifikasi GitHub Education.

</div>

## Apa Itu GitHub Education Verify?

GitHub Education Verify adalah proses verifikasi status pelajar atau pengajar agar akun GitHub bisa mengakses benefit GitHub Education.

Project ini dibuat untuk membantu proses tersebut secara lebih terstruktur melalui:

- Bot Telegram untuk interaksi pengguna
- Backend API untuk kebutuhan web/integrasi
- Sistem log, status, dan pengelolaan data verifikasi

## Fitur Utama

- Verifikasi Student dan Teacher
- Bot Telegram untuk user dan owner/admin
- API backend berbasis Flask
- Sistem kredit (referral, daily check-in, top up)
- Konfigurasi multi-sekolah
- Logging dan penyimpanan status verifikasi

## Requirements

- Python 3.10+
- Pip
- Telegram credentials: BOT_TOKEN, API_ID, API_HASH
- Dependensi Python di [requirements.txt](requirements.txt)

## Instalasi

1. Clone repository
2. Masuk ke folder project
3. Install dependency

```bash
pip install -r requirements.txt
```

## Konfigurasi Environment (.env)

### Linux/macOS

```bash
cp .env.example .env
```

### Windows PowerShell

```powershell
Copy-Item .env.example .env
```

### Variabel Minimal

Isi nilai berikut di `.env`:

- BOT_TOKEN
- API_ID
- API_HASH
- OWNER_ID
- API_SECRET

### Contoh Konfigurasi Data Sekolah di .env

```env
SCHOOL_COUNT=2

SCHOOL_1_ENABLED=1
SCHOOL_1_CODE=sma_negeri_1_ngawi
SCHOOL_1_MODE=private
SCHOOL_1_NAME=SMA Negeri 1 Ngawi
SCHOOL_1_GITHUB_SCHOOL_ID=123456
SCHOOL_1_ADDRESS=Jl Raya Suki KP 07, Ngawi, Pekalongan 12345
SCHOOL_1_PHONE=(1234) 123456
SCHOOL_1_PRINCIPAL_NAME=Drs. Amba, M.Pd
SCHOOL_1_PRINCIPAL_NIP=123456789
SCHOOL_1_CITY=Ngawi
SCHOOL_1_PROVINCE=Jawa Tengah
SCHOOL_1_LOGO_PATH=logo/logosekolah.png
SCHOOL_1_LAT=-11.11
SCHOOL_1_LON=123.123

SCHOOL_2_ENABLED=1
SCHOOL_2_CODE=sma_negeri_2_ngawi
SCHOOL_2_MODE=public
SCHOOL_2_NAME=SMA Negeri 2 Ngawi
SCHOOL_2_GITHUB_SCHOOL_ID=654321
SCHOOL_2_ADDRESS=Jl Raya Suki KP 08, Ngawi, Pekalongan 12345
SCHOOL_2_PHONE=(1234) 654321
SCHOOL_2_PRINCIPAL_NAME=Drs. Bimba, M.Pd
SCHOOL_2_PRINCIPAL_NIP=987654321
SCHOOL_2_CITY=Ngawi
SCHOOL_2_PROVINCE=Jawa Tengah
SCHOOL_2_LOGO_PATH=logo/logosekolah2.png
SCHOOL_2_LAT=-11.12
SCHOOL_2_LON=123.124
```

## Menjalankan Project

### Jalankan Semua Sekaligus (disarankan)

```bash
python run_all.py
```

### Jalankan Manual

```bash
python bot.py
```

```bash
python api_server.py
```

## Catatan Penting

- Jangan upload file `.env` ke GitHub
- Simpan session Telegram dengan aman
- Gunakan API_SECRET yang kuat untuk production