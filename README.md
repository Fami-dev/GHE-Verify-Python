<div align="center">

# GHE Verify Python

Bot Telegram + backend API untuk membantu alur verifikasi GitHub Education.

</div>

## Apa Itu GitHub Education Verify?

GitHub Education Verify adalah proses verifikasi status pelajar atau pengajar agar akun GitHub dapat mengakses manfaat GitHub Education.

Project ini dibuat untuk membantu proses tersebut secara lebih terstruktur melalui:

- Bot Telegram untuk interaksi pengguna
- Backend API untuk kebutuhan web dan integrasi
- Sistem log, status, dan pengelolaan data verifikasi

## Fitur Utama

- Verifikasi Siswa dan Guru
- Bot Telegram untuk pengguna dan owner/admin
- API backend berbasis Flask
- Sistem kredit (referral, check-in harian, top up)
- Konfigurasi multi-sekolah
- Logging dan penyimpanan status verifikasi

## Kebutuhan Sistem

- Python 3.10+
- Pip
- Kredensial Telegram: BOT_TOKEN, API_ID, API_HASH
- Dependensi Python di [requirements.txt](requirements.txt)

## Instalasi

1. Clone repositori
2. Masuk ke folder project
3. Install dependensi

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
SCHOOL_COUNT=2 # jumlah total sekolah yang dikonfigurasi

SCHOOL_1_ENABLED=1 # 1 aktif, 0 nonaktif
SCHOOL_1_CODE=sma_negeri_1_ngawi # kode unik sekolah (tanpa spasi)
SCHOOL_1_MODE=private # public atau private
SCHOOL_1_NAME=SMA Negeri 1 Ngawi # nama lengkap sekolah
SCHOOL_1_GITHUB_SCHOOL_ID=123456 # ID sekolah GitHub Education (dari payload)
SCHOOL_1_ADDRESS=Jl Raya Suki KP 07, Ngawi, Pekalongan 12345 # alamat sekolah
SCHOOL_1_PHONE=(1234) 123456 # nomor telepon sekolah
SCHOOL_1_PRINCIPAL_NAME=Drs. Amba, M.Pd # nama kepala sekolah
SCHOOL_1_PRINCIPAL_NIP=123456789 # NIP kepala sekolah
SCHOOL_1_CITY=Ngawi # kota sekolah
SCHOOL_1_PROVINCE=Jawa Tengah # provinsi sekolah
SCHOOL_1_LOGO_PATH=logo/logosekolah.png # path file logo sekolah
SCHOOL_1_LAT=-11.11 # koordinat latitude sekolah
SCHOOL_1_LON=123.123 # koordinat longitude sekolah

SCHOOL_2_ENABLED=1 # 1 aktif, 0 nonaktif
SCHOOL_2_CODE=sma_negeri_2_ngawi # kode unik sekolah (tanpa spasi)
SCHOOL_2_MODE=public # public atau private
SCHOOL_2_NAME=SMA Negeri 2 Ngawi # nama lengkap sekolah
SCHOOL_2_GITHUB_SCHOOL_ID=654321 # ID sekolah GitHub Education (dari payload)
SCHOOL_2_ADDRESS=Jl Raya Suki KP 08, Ngawi, Pekalongan 12345 # alamat sekolah
SCHOOL_2_PHONE=(1234) 654321 # nomor telepon sekolah
SCHOOL_2_PRINCIPAL_NAME=Drs. Bimba, M.Pd # nama kepala sekolah
SCHOOL_2_PRINCIPAL_NIP=987654321 # NIP kepala sekolah
SCHOOL_2_CITY=Ngawi # kota sekolah
SCHOOL_2_PROVINCE=Jawa Tengah # provinsi sekolah
SCHOOL_2_LOGO_PATH=logo/logosekolah2.png # path file logo sekolah
SCHOOL_2_LAT=-11.12 # koordinat latitude sekolah
SCHOOL_2_LON=123.124 # koordinat longitude sekolah
```

## Menjalankan Proyek

### Jalankan Semua Sekaligus (Disarankan)

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