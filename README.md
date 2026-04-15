# 📈 Gemini IDX Technical Analyst

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![Gemini AI](https://img.shields.io/badge/Google%20Gemini-AI-orange?style=for-the-badge&logo=google)
![Telegram API](https://img.shields.io/badge/Telegram-Bot-informational?style=for-the-badge&logo=telegram)
![GitHub Actions](https://img.shields.io/badge/Automated-Cron%20Job-success?style=for-the-badge&logo=github-actions)

**Gemini IDX Technical Analyst** adalah bot analitik otomatis yang mengintegrasikan data pasar saham Indonesia (IHSG), kalkulasi indikator teknikal tingkat lanjut, dan kecerdasan buatan (LLM). Repositori ini bertindak sebagai *Senior Technical Analyst* virtual yang memberikan laporan harian komprehensif langsung ke Telegram Anda.

---

## 🏛️ Arsitektur Sistem

Sistem ini dibangun dengan pendekatan modular, memisahkan ekstraksi data, pemrosesan logika, dan interpretasi AI:

1. **Data Ingestion:** `yfinance` mengambil data harga historis saham (OHLCV).
2. **Technical Engine:** `pandas_ta` menghitung indikator kunci (Moving Averages, RSI, MACD, Bollinger Bands, MFI) dan mengidentifikasi Support/Resistance.
3. **AI Interpretation:** Google Gemini AI (1.5 Flash) memproses data kuantitatif menjadi narasi kualitatif dan strategi *trading* (BoW, Breakout, dll).
4. **Delivery & Automation:** Laporan dikirim ke Telegram menggunakan format Markdown, dijalankan secara otonom setiap hari pukul 08:00 WIB via **GitHub Actions**.

---

## 📋 Prasyarat (*Prerequisites*)

Sebelum memulai implementasi, pastikan Anda telah memiliki:

- Akun **Google AI Studio** untuk mendapatkan `GEMINI_API_KEY`.
- Akun Telegram dan telah membuat bot melalui **@BotFather** untuk mendapatkan `TELEGRAM_BOT_TOKEN`.
- ID Chat/Channel Telegram Anda (`TELEGRAM_CHAT_ID`).
- Repositori GitHub untuk menjalankan *workflow* otomatis.

---

## 🚀 Panduan Instalasi (Lokal)

Jika Anda ingin menguji coba skrip ini di environment lokal Anda sebelum mengunggahnya ke GitHub Actions, ikuti langkah berikut:

### 1. Kloning Repositori

```bash
git clone https://github.com/USERNAME_ANDA/gemini-idx-technical-analyst.git
cd gemini-idx-technical-analyst
```

### 2. Konfigurasi Virtual Environment (Opsional namun disarankan)

```bash
python -m venv venv
source venv/bin/activate  # Untuk Linux/Mac
venv\Scripts\activate     # Untuk Windows
```

### 3. Instalasi Dependensi

```bash
pip install -r requirements.txt
```

### 4. Konfigurasi Environment Variables

Buat file `.env` di root direktori (pastikan file ini masuk ke `.gitignore`) dan masukkan kredensial Anda:

```env
GEMINI_API_KEY="AIzaSyYourGeminiKeyHere..."
TELEGRAM_BOT_TOKEN="123456789:ABCdefGhIjkL..."
TELEGRAM_CHAT_ID="-100123456789"
```

### 5. Atur Daftar Saham

Buka file `saham_pantauan.txt` dan masukkan kode emiten yang ingin dianalisis (satu kode per baris). Sistem otomatis menambahkan `.JK` di backend.

```text
BBCA
BBRI
TLKM
AMMN
```

### 6. Eksekusi Skrip

```bash
python bot_saham.py
```

---

## ⚙️ Konfigurasi Otomasi (GitHub Actions)

Repositori ini sudah dilengkapi dengan file `.github/workflows/daily_report.yml` agar skrip berjalan otomatis setiap hari kerja pukul 08:00 WIB.

Untuk mengaktifkannya:

1. Masuk ke halaman repositori GitHub Anda.
2. Navigasi ke **Settings > Secrets and variables > Actions**.
3. Klik **New repository secret** dan tambahkan 3 secrets berikut sesuai dengan kredensial Anda:
   - `GEMINI_API_KEY`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`

GitHub Actions akan otomatis mengambil data dari `saham_pantauan.txt` dan mengirimkan laporan setiap pagi.

---

## 🛡️ Disclaimer

Skrip dan repositori ini dibuat murni untuk tujuan edukasi, penelitian, dan penyediaan informasi kuantitatif. Segala bentuk keputusan investasi atau trading yang didasarkan pada output sistem ini sepenuhnya menjadi tanggung jawab pengguna. Do Your Own Research (DYOR).

---

Developed with clean code and structured analytics.
