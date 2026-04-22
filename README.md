# 📈 IDX Technical Analyst Hybrid Engine PRO

![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python)
![Pandas TA](https://img.shields.io/badge/Pandas_TA-Technical_Engine-success?style=for-the-badge)
![Gemini AI](https://img.shields.io/badge/Google%20Gemini-Optional_AI-orange?style=for-the-badge&logo=google)
![OpenRouter](https://img.shields.io/badge/OpenRouter-Optional_AI-black?style=for-the-badge)
![Telegram API](https://img.shields.io/badge/Telegram-Bot-informational?style=for-the-badge&logo=telegram)
![Yahoo Finance](https://img.shields.io/badge/YFinance-Market_Data-4CAF50?style=for-the-badge)

**IDX Technical Analyst Hybrid Engine PRO** adalah bot analitik otomatis untuk saham Indonesia yang menggabungkan **data pasar Yahoo Finance**, **engine teknikal rule-based Python**, **screener saham syariah live**, **Telegram Bot**, dan **AI insight opsional**.

Versi PRO ini menambahkan:
- **Decision Engine** yang lebih tegas
- **Dynamic entry trigger**
- **Dua skenario trading**: pullback & breakout
- **Smart stop loss** dengan batas maksimum 5%
- **Position sizing**
- **Setup grade** dan status `ENTRY READY / WAIT FOR TRIGGER / SKIP`

Dengan pendekatan ini, bot tidak hanya memberi level statis, tetapi juga memberi konteks eksekusi dan manajemen risiko yang lebih realistis.

---

## 🏛️ Arsitektur Sistem

1. **Universe Builder**
   - Bot mengunduh PDF **DES OJK**
   - Mengekstrak ticker saham syariah
   - Menyimpan ke:
     - `data/syariah_stocks_master.txt`
     - `data/syariah_stocks.txt`

2. **Data Ingestion**
   - `yfinance` mengambil data OHLCV harian
   - Ticker IDX otomatis dinormalisasi ke `.JK`
   - Mendukung batch screening

3. **Technical Engine PRO**
   - Hitung indikator teknikal:
     - SMA 10 / 20 / 50 / 200
     - RSI
     - MACD
     - Bollinger Bands
     - MFI
     - ATR
     - Volume SMA 20
   - Hasil analisa:
     - trend
     - market phase
     - support/resistance
     - pullback trigger
     - breakout trigger
     - risk-reward
     - position sizing

4. **Decision Engine**
   - Menentukan status:
     - `ENTRY READY`
     - `WAIT FOR TRIGGER`
     - `SKIP`
   - Menetapkan setup grade:
     - `A`
     - `B`
     - `C`
     - `Avoid`

5. **Telegram Delivery**
   - Kirim hasil screener
   - Kirim analisa teknikal lengkap
   - Kirim alert error

6. **AI Insight Opsional**
   - Gemini
   - OpenRouter

---

## 📋 Fitur Utama

### 1. Screener Saham Syariah Live
Kriteria utama:
- Harga saham **< 100**
- Return harian positif
- Volume > 1.5x rata-rata 20 hari
- `Close > SMA20 > SMA50`
- RSI minimum sesuai threshold
- MACD bullish
- Nilai transaksi minimum

### 2. Dynamic Entry Trigger
Bot tidak lagi hanya menulis “entry di level X”, tetapi memisahkan:
- **Pullback Entry**
- **Breakout Entry**

Dengan trigger seperti:
- bullish candle
- rebound
- volume naik
- breakout + volume spike

### 3. Smart Stop Loss
SL dibatasi agar tetap realistis:
- berdasarkan struktur teknikal
- dibatasi **maksimum 5%** dari entry

### 4. Position Sizing
Bot menghitung:
- modal
- risk per trade
- risk nominal
- maksimum posisi
- estimasi lot

### 5. Decision Engine
Output utama:
- Trend
- Kondisi
- RR Status
- Action
- Grade

---

## 📁 Struktur Folder

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

## 🚀 Instalasi Lokal

### 1. Clone repo
```bash
git clone https://github.com/USERNAME_ANDA/IDX-Technical-Analyst-Hybrid-Engine.git
cd IDX-Technical-Analyst-Hybrid-Engine
```

### 2. Buat virtual environment
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

### 3. Install dependency
```bash
pip install -r requirements.txt
```

---

## ⚙️ Requirements

```txt
requests
pandas
yfinance
pandas_ta
pypdf
google-genai
```

---

## 🔐 Environment Variables

Buat file `.env` berdasarkan `.env.example`.

Contoh penting:

```env
RUN_MODE=screener_syariah
SCREENER_MAX_PRICE=100
MIN_ACCEPTABLE_RR=1.2
ACCOUNT_SIZE=3000000
RISK_PER_TRADE_PCT=1
MAX_STOP_PCT=5
```

Keterangan:
- `SCREENER_MAX_PRICE`: filter harga maksimum saham
- `MIN_ACCEPTABLE_RR`: RR minimum agar setup layak
- `ACCOUNT_SIZE`: modal akun
- `RISK_PER_TRADE_PCT`: risk per trade dalam persen
- `MAX_STOP_PCT`: batas maksimum SL dari entry

---

## ▶️ Mode Penggunaan

### Watchlist
```env
RUN_MODE=watchlist
```

### Screener Syariah
```env
RUN_MODE=screener_syariah
```

### Hybrid
```env
RUN_MODE=hybrid
```

Jalankan:
```bash
python bot_saham.py
```

---

## 📤 Contoh Output Telegram

```text
📊 ANALISIS TEKNIKAL — $XXXX (Daily)

1. Decision Engine
• Trend      : Bullish continuation / breakout confirmation
• Kondisi    : Overextended / breakout kuat
• RR Status  : Sehat
• Action     : WAIT FOR TRIGGER
• Grade      : C

4. Skenario Pullback Entry
• Area       : 134
• Trigger    : Bullish candle + rebound + volume naik
• Status     : WAIT
• Entry      : 134
• SL         : 128
• TP         : 149 | 153
• RR         : 2.4

5. Skenario Breakout Entry
• Area       : >145
• Trigger    : Breakout + volume spike
• Status     : VALID
• Entry      : 146
• SL         : 139
• TP         : 153 | 158
• RR         : 1.71
```

---

## ⚙️ GitHub Actions

Simpan workflow di:
```text
.github/workflows/daily_report.yml
```

Workflow final sudah disesuaikan untuk:
- mode `screener_syariah`
- harga `< 100`
- risk-reward minimum
- position sizing
- smart stop loss
- debug runtime config

---

## 🔑 GitHub Secrets

Tambahkan di:
**Settings → Secrets and variables → Actions**

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `GEMINI_API_KEY` *(opsional)*
- `OPENROUTER_API_KEY` *(opsional)*

---

## 🛠️ Roadmap

- Backtest hasil screener
- Simpan history kandidat ke CSV / SQLite
- Heatmap saham syariah
- Multi-timeframe engine
- Relative strength ranking
- Dashboard web

---

## 🛡️ Disclaimer

Tools ini dibuat untuk tujuan edukasi, riset, dan otomasi analisa teknikal.  
Semua hasil screener, report rule-based, dan insight AI **bukan rekomendasi investasi mutlak**.

Segala keputusan beli, jual, atau trading tetap menjadi tanggung jawab pengguna.

**Do Your Own Research (DYOR).**
