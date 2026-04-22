# 📈 IDX Technical Analyst Hybrid Engine

![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python)
![Pandas TA](https://img.shields.io/badge/Pandas_TA-Technical_Engine-success?style=for-the-badge)
![Gemini AI](https://img.shields.io/badge/Google%20Gemini-Optional_AI-orange?style=for-the-badge&logo=google)
![OpenRouter](https://img.shields.io/badge/OpenRouter-Optional_AI-black?style=for-the-badge)
![Telegram API](https://img.shields.io/badge/Telegram-Bot-informational?style=for-the-badge&logo=telegram)
![Yahoo Finance](https://img.shields.io/badge/YFinance-Market_Data-4CAF50?style=for-the-badge)

**IDX Technical Analyst Hybrid Engine** adalah bot analitik otomatis untuk saham Indonesia yang mengintegrasikan **data pasar dari Yahoo Finance**, **engine analisa teknikal rule-based berbasis Python**, **screener saham syariah live**, **Telegram Bot**, serta **AI insight opsional**.

Versi terbaru menggunakan pendekatan **Hybrid Deterministic Engine**, di mana **Python Rule-Based Engine** menjadi inti utama pengambilan keputusan analisa teknikal dan screening, sementara AI seperti **Gemini** atau **OpenRouter** hanya berfungsi sebagai pemberi insight tambahan. Dengan pendekatan ini, bot tetap dapat berjalan stabil walaupun layanan AI sedang gagal, rate limit, atau dinonaktifkan.

---

## 🏛️ Arsitektur Sistem (Hybrid & Fault-Tolerant)

Sistem dirancang modular dan tahan gagal dengan alur kerja berikut:

1. **Universe Builder (Syariah Auto Update):**
   - Bot dapat mengunduh PDF **Daftar Efek Syariah (DES) OJK**
   - Mengekstrak kode saham secara otomatis
   - Menyimpan hasil ke file:
     - `data/syariah_stocks_master.txt`
     - `data/syariah_stocks.txt`

2. **Data Ingestion:**
   - `yfinance` mengambil data pasar **OHLCV** harian
   - Sistem menangani normalisasi ticker `.JK`
   - Mendukung batch download untuk screening banyak saham sekaligus

3. **Deterministic Technical Engine:**
   - `pandas_ta` dan Python menghitung indikator teknikal:
     - SMA 10 / 20 / 50 / 200
     - RSI
     - MACD
     - Bollinger Bands
     - Money Flow Index (MFI)
     - Volume SMA 20
   - Engine kemudian membentuk:
     - struktur harga
     - market phase
     - support & resistance
     - skenario entry / TP / SL
     - ranking screener

4. **Syariah Screener Engine:**
   - Melakukan scanning otomatis seluruh universe saham syariah
   - Menyaring kandidat berdasarkan:
     - harga murah
     - volume meningkat
     - return harian positif
     - trend bullish valid
     - likuiditas minimum
   - Kandidat terbaik diteruskan ke modul analisa teknikal

5. **AI Insight (Opsional):**
   - Bot dapat meminta insight tambahan dari:
     - **Gemini**
     - **OpenRouter**
   - Jika AI gagal, bot tetap mengirim laporan utama tanpa hambatan

6. **Delivery Layer:**
   - Laporan screener dan analisa teknikal dikirim ke **Telegram**
   - Eksekusi dapat berjalan:
     - secara lokal
     - melalui **GitHub Actions**
     - secara terjadwal saat jam bursa

---

## 📋 Prasyarat (*Prerequisites*)

Sebelum menjalankan project ini, siapkan:

- Python **3.12**
- Token bot Telegram dari **@BotFather**
- ID chat / channel Telegram
- Koneksi internet untuk mengambil data dari Yahoo Finance
- Opsional:
  - **Google AI Studio** untuk `GEMINI_API_KEY`
  - **OpenRouter** untuk `OPENROUTER_API_KEY`

---

## 📊 Fitur Utama

### 1. Analisa Teknikal Otomatis
Bot menghasilkan analisa teknikal saham Indonesia berbasis **Python rule-based engine**.

Indikator yang digunakan:
- SMA 10 / 20 / 50 / 200
- RSI 14
- MACD
- Bollinger Bands
- Volume SMA 20
- MFI 14

Output analisa meliputi:
- Tren utama
- Struktur harga
- Market phase
- Momentum
- Volume & money flow
- Support & resistance
- Strategi entry, TP, dan SL

---

### 2. Screener Saham Syariah Live
Bot dapat melakukan screening otomatis terhadap seluruh saham syariah aktif berdasarkan data pasar terbaru dari Yahoo Finance.

Kriteria utama screener:
- Harga saham `<= 500`
- Return 1 hari positif
- Volume > rata-rata volume 20 hari
- `Close > SMA20 > SMA50`
- RSI minimum sesuai threshold
- MACD bullish
- Nilai transaksi minimum untuk menjaga likuiditas

Hasil screener akan diurutkan berdasarkan skor prioritas, lalu saham terbaik akan dianalisa lebih lanjut oleh modul teknikal.

---

### 3. Auto Update Universe Saham Syariah
Bot dapat memperbarui daftar saham syariah otomatis dari **DES OJK**.

Proses:
- download PDF DES resmi
- ekstrak kode saham
- simpan ke file master
- buat file screener operasional
- tambahkan penyesuaian manual jika diperlukan

Dengan fitur ini, Anda tidak perlu mengelola universe saham syariah sepenuhnya secara manual.

---

### 4. Multi Mode Operation
Bot mendukung tiga mode utama:

#### `watchlist`
Mode lama berbasis daftar saham manual pada file `data/saham_pantauan.txt`.

#### `screener_syariah`
Mode otomatis penuh:
- update universe saham syariah
- scan live market data
- kirim shortlist
- lanjut analisa teknikal kandidat terbaik

#### `hybrid`
Mode gabungan:
- jalankan screener syariah live
- analisa kandidat hasil screener
- analisa tambahan watchlist manual yang belum masuk shortlist

---

### 5. Telegram Integration
Bot mengirim hasil ke Telegram dalam format yang mudah dibaca, meliputi:
- hasil screener
- shortlist saham syariah trending
- analisa teknikal lengkap per saham
- notifikasi error / kegagalan fetch data

---

### 6. AI Insight Opsional
Setelah report utama selesai dibuat oleh engine Python, bot dapat menambahkan insight AI tambahan.

Provider yang didukung:
- Gemini
- OpenRouter

AI insight bersifat **opsional**, dan dapat dimatikan penuh bila Anda ingin hanya memakai engine rule-based.

---

## 📁 Struktur Folder Final

```bash
IDX-Technical-Analyst-Hybrid-Engine/
├── .github/
│   └── workflows/
│       └── daily_report.yml
├── data/
│   ├── saham_pantauan.txt
│   ├── syariah_stocks.txt
│   ├── syariah_stocks_master.txt
│   └── des_syariah_latest.pdf
├── bot_saham.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── LICENSE
```

---

## 📄 Fungsi File

### `bot_saham.py`
File utama bot yang berisi:
- updater universe syariah
- screener live
- analisa teknikal
- formatter laporan
- Telegram sender
- AI insight opsional

### `data/saham_pantauan.txt`
Daftar saham manual untuk mode `watchlist` atau tambahan di mode `hybrid`.

Contoh:
```text
BBRI
TLKM
BRIS
BUMI
```

### `data/syariah_stocks_master.txt`
Master universe saham syariah hasil ekstraksi DES OJK.

### `data/syariah_stocks.txt`
Universe final yang dipakai screener live.

### `data/des_syariah_latest.pdf`
Cache PDF DES yang diunduh otomatis oleh bot.

### `.github/workflows/daily_report.yml`
Workflow GitHub Actions untuk eksekusi otomatis.

---

## 🚀 Panduan Instalasi (Lokal)

### 1. Kloning Repositori

```bash
git clone https://github.com/USERNAME_ANDA/IDX-Technical-Analyst-Hybrid-Engine.git
cd IDX-Technical-Analyst-Hybrid-Engine
```

### 2. Buat Virtual Environment & Instalasi Dependency

```bash
python -m venv venv
```

#### Linux / macOS
```bash
source venv/bin/activate
```

#### Windows
```bash
venv\Scripts\activate
```

Lalu install dependency:

```bash
pip install -r requirements.txt
```

---

## ⚙️ Requirements

Isi `requirements.txt` minimal:

```txt
requests
pandas
yfinance
pandas_ta
pypdf
google-genai
```

---

## 🔐 Konfigurasi Environment Variables

Buat file `.env` di root project berdasarkan `.env.example`.

Contoh:

```env
TELEGRAM_BOT_TOKEN=isi_token_bot
TELEGRAM_CHAT_ID=isi_chat_id

RUN_MODE=screener_syariah
WATCHLIST_FILE=data/saham_pantauan.txt
SYARIAH_UNIVERSE_FILE=data/syariah_stocks.txt
SYARIAH_MASTER_FILE=data/syariah_stocks_master.txt
DES_PDF_LOCAL=data/des_syariah_latest.pdf

DES_PDF_URL=https://ojk.go.id/id/kanal/syariah/data-dan-statistik/daftar-efek-syariah/Documents/Pages/Daftar-Efek-Syariah-KEP59D042025/SK%20DES%20Periode%20II%202025%20%28Lampiran%20I%29.pdf

SCREENER_LIMIT=5
SCREENER_PERIOD=6mo
SCREENER_INTERVAL=1d
SCREENER_MAX_PRICE=500
SCREENER_MIN_VOLUME_RATIO=1.5
SCREENER_MIN_VALUE_TRADED=1000000000
SCREENER_MIN_RSI=55
SCREENER_BATCH_SIZE=40
SCREENER_DELAY_SECONDS=1.0
SCREENER_ENABLE_AUTO_UPDATE_UNIVERSE=1

ENABLE_AI_INSIGHT=0
AI_PROVIDER=off
GEMINI_API_KEY=
OPENROUTER_API_KEY=

INCIDENTAL_ADDITIONS=BSAI
EXCLUDED_CODES=ALDI,BRAU,CPDW,INSA,MASA,RINA,SIMM,SING,SQBB,TRUE
TELEGRAM_PREFIX=
```

---

## ▶️ Mode Penggunaan

### 1. Watchlist Mode

Mode ini membaca file `data/saham_pantauan.txt`.

```env
RUN_MODE=watchlist
```

Jalankan:
```bash
python bot_saham.py
```

---

### 2. Screener Syariah Mode

Mode ini akan:
- update universe syariah otomatis
- scan saham syariah live
- kirim shortlist ke Telegram
- analisa teknikal kandidat terbaik

```env
RUN_MODE=screener_syariah
```

Jalankan:
```bash
python bot_saham.py
```

---

### 3. Hybrid Mode

Mode ini akan:
- scan saham syariah live
- analisa shortlist hasil screener
- analisa tambahan watchlist manual

```env
RUN_MODE=hybrid
```

Jalankan:
```bash
python bot_saham.py
```

---

## 📤 Contoh Output Telegram

### Screener
```text
📌 Screener Saham Syariah Trending

Kriteria:
• Harga ≤ 500
• Volume > 1.5x rata-rata 20 hari
• Return harian positif
• Close > SMA20 > SMA50
• RSI dan MACD bullish

1. $BUMI
   Harga     : 122
   Return 1D : 6.09%
   Vol Ratio : 2.41x
   Value     : 12.40B
   RSI       : 67.3
   Score     : 84.6
```

### Analisa teknikal
```text
📊 ANALISIS TEKNIKAL — $BUMI (Daily)

1. Tren Utama
• Kondisi : Uptrend kuat
• Bias    : Bullish kuat
...
```

---

## ⚙️ Konfigurasi Otomasi (GitHub Actions)

Untuk menjalankan bot secara otomatis, gunakan workflow berikut:

Simpan sebagai:
```text
.github/workflows/daily_report.yml
```

Contoh:

```yaml
name: Daily Stock Analysis Report

on:
  schedule:
    - cron: '0 2-9 * * 1-5'
  workflow_dispatch:

jobs:
  analyze_and_report:
    runs-on: ubuntu-latest
    timeout-minutes: 30

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Prepare data directory
        run: |
          mkdir -p data
          touch data/saham_pantauan.txt
          touch data/syariah_stocks.txt
          touch data/syariah_stocks_master.txt

      - name: Run stock bot
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}

          RUN_MODE: screener_syariah
          AI_PROVIDER: off
          ENABLE_AI_INSIGHT: "0"

          WATCHLIST_FILE: data/saham_pantauan.txt
          SYARIAH_UNIVERSE_FILE: data/syariah_stocks.txt
          SYARIAH_MASTER_FILE: data/syariah_stocks_master.txt
          DES_PDF_LOCAL: data/des_syariah_latest.pdf

          SCREENER_LIMIT: "5"
          SCREENER_PERIOD: "6mo"
          SCREENER_INTERVAL: "1d"
          SCREENER_MAX_PRICE: "500"
          SCREENER_MIN_VOLUME_RATIO: "1.5"
          SCREENER_MIN_VALUE_TRADED: "1000000000"
          SCREENER_MIN_RSI: "55"
          SCREENER_BATCH_SIZE: "40"
          SCREENER_DELAY_SECONDS: "1.0"
          SCREENER_ENABLE_AUTO_UPDATE_UNIVERSE: "1"

          INCIDENTAL_ADDITIONS: "BSAI"
          EXCLUDED_CODES: "ALDI,BRAU,CPDW,INSA,MASA,RINA,SIMM,SING,SQBB,TRUE"

          TELEGRAM_PREFIX: "🤖 Screener Syariah"
        run: |
          python bot_saham.py
```

---

## 🔑 GitHub Secrets yang Dibutuhkan

Tambahkan secrets berikut di GitHub repository:

**Settings → Secrets and variables → Actions**

### Secrets:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `GEMINI_API_KEY` *(opsional)*
- `OPENROUTER_API_KEY` *(opsional)*

Jika AI insight tidak digunakan, API key AI dapat dikosongkan.

---

## 🔄 Alur Kerja Internal Bot

1. cek / update PDF DES
2. ekstrak universe saham syariah
3. bangun file master dan file screener
4. ambil data harga dari Yahoo Finance
5. hitung indikator teknikal
6. lakukan screening kandidat
7. urutkan berdasarkan skor
8. kirim shortlist ke Telegram
9. analisa teknikal kandidat terbaik
10. kirim report final

---

## 🛠️ Roadmap Pengembangan

### Phase 1: Penyempurnaan Engine
- Backtest hasil screener
- Penyimpanan history kandidat harian ke CSV / SQLite
- Optimasi ranking dan scoring

### Phase 2: Visualisasi & Dashboard
- Dashboard web hasil screening
- Heatmap saham syariah
- Rekap performa sinyal

### Phase 3: Ekspansi Analisa
- Analisa multi-timeframe
- Relative strength ranking
- Filter berbasis sektor
- Integrasi data fundamental
- Peringatan breakout intraday

---

## 🛡️ Disclaimer

Tools ini dibuat untuk tujuan edukasi, riset, dan otomasi analisa teknikal.  
Semua hasil screener, report rule-based, dan insight AI **bukan merupakan rekomendasi investasi mutlak**.

Segala keputusan beli, jual, atau trading sepenuhnya menjadi tanggung jawab pengguna.

**Do Your Own Research (DYOR).**

---

## License

```text
GNU General Public License v3.0
```
