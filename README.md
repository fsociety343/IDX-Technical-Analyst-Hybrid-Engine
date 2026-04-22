# 📈 IDX Technical Analyst Hybrid Engine PRO v2

![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python)
![Pandas TA](https://img.shields.io/badge/Pandas_TA-Technical_Engine-success?style=for-the-badge)
![Gemini AI](https://img.shields.io/badge/Google%20Gemini-Optional_AI-orange?style=for-the-badge&logo=google)
![OpenRouter](https://img.shields.io/badge/OpenRouter-Optional_AI-black?style=for-the-badge)
![Telegram API](https://img.shields.io/badge/Telegram-Bot-informational?style=for-the-badge&logo=telegram)
![Yahoo Finance](https://img.shields.io/badge/YFinance-Market_Data-4CAF50?style=for-the-badge)

**IDX Technical Analyst Hybrid Engine PRO v2** adalah bot analitik otomatis untuk saham Indonesia yang menggabungkan **data pasar Yahoo Finance**, **engine teknikal rule-based Python**, **screener saham syariah live**, **Telegram Bot**, dan **AI insight opsional**.

Versi **PRO v2** menambahkan:
- **Decision Engine** yang lebih disiplin
- **Dynamic entry trigger**
- **Dua skenario trading**: pullback & breakout
- **Breakout buffer** untuk mengurangi fake breakout
- **Pullback expiry** agar setup tidak menggantung terlalu lama
- **Market filter IHSG**
- **Smart stop loss**: tactical & structural stop
- **Position sizing**
- **Trade management** setelah entry

Dengan pendekatan ini, bot tidak hanya memberi level statis, tetapi juga memberi konteks eksekusi, manajemen risiko, dan disiplin market filter yang lebih realistis.

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

3. **Technical Engine PRO v2**
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
     - breakout buffer
     - tactical vs structural stop
     - risk-reward
     - position sizing
     - trade management

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

5. **Market Filter**
   - Memeriksa kondisi **IHSG / `^JKSE`**
   - Setup hanya ditingkatkan menjadi `ENTRY READY` jika market mendukung
   - Jika market lemah, setup akan ditahan di `WAIT FOR TRIGGER` atau `SKIP`

6. **Telegram Delivery**
   - Kirim hasil screener
   - Kirim analisa teknikal lengkap
   - Kirim alert error

7. **AI Insight Opsional**
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
- Market filter IHSG mendukung

### 2. Dynamic Entry Trigger
Bot memisahkan:
- **Pullback Entry**
- **Breakout Entry**

Dengan trigger seperti:
- bullish candle
- rebound
- volume naik
- breakout + volume spike

### 3. Breakout Buffer
Breakout entry tidak lagi tepat di resistance.  
Bot menambahkan:
- buffer persentase
- buffer absolut

Tujuannya mengurangi fake breakout.

### 4. Pullback Expiry
Setup pullback memiliki masa berlaku:
- default `3–5 hari bursa`
- bila tidak tersentuh / tidak terkonfirmasi, setup dianggap expired secara operasional

### 5. Smart Stop Loss
Bot menampilkan:
- **Tactical SL** → lebih efisien untuk RR
- **Structural SL** → lebih longgar, berbasis struktur support

### 6. Position Sizing
Bot menghitung:
- modal
- risk per trade
- risk nominal
- maksimum nilai posisi
- estimasi lot

### 7. Trade Management
Setelah entry:
- jika harga naik **+5%**, SL digeser ke **BEP**
- jika harga mencapai **TP1**, ambil **partial profit 50%**
- sisa posisi diarahkan ke **TP2**

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

Variabel penting:

```env
RUN_MODE=screener_syariah
SCREENER_MAX_PRICE=100
MIN_ACCEPTABLE_RR=1.2
ACCOUNT_SIZE=3000000
RISK_PER_TRADE_PCT=1
MAX_STOP_PCT=5

BREAKOUT_BUFFER_PCT=1
BREAKOUT_BUFFER_ABS=1
PULLBACK_EXPIRY_DAYS=5
USE_MARKET_FILTER=1
MARKET_SYMBOL=^JKSE
MOVE_SL_TO_BEP_AT_PCT=5
PARTIAL_TAKE_PROFIT_AT_TP1_PCT=50
```

Keterangan:
- `BREAKOUT_BUFFER_PCT`: buffer persentase breakout
- `BREAKOUT_BUFFER_ABS`: buffer absolut breakout
- `PULLBACK_EXPIRY_DAYS`: masa berlaku setup pullback
- `USE_MARKET_FILTER`: aktifkan filter IHSG
- `MARKET_SYMBOL`: simbol index market, default `^JKSE`
- `MOVE_SL_TO_BEP_AT_PCT`: kapan SL digeser ke BEP
- `PARTIAL_TAKE_PROFIT_AT_TP1_PCT`: persentase partial profit di TP1

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
• Kondisi    : Bullish sehat
• Market     : Uptrend / mendukung
• RR Status  : Sehat
• Action     : WAIT FOR TRIGGER
• Grade      : B

4. Skenario Pullback Entry
• Area         : 134
• Trigger      : Bullish candle + rebound + volume naik
• Status       : WAIT
• Entry        : 134
• Tactical SL  : 130
• Structural SL: 128
• TP           : 149 | 153
• RR Tactical  : 3.0
• RR Structural: 2.2
• Expiry       : 5 hari bursa

5. Skenario Breakout Entry
• Area         : >145
• Trigger      : Close breakout + volume spike + buffer 1.00%
• Status       : VALID
• Entry        : 146
• Tactical SL  : 139
• Structural SL: 138
• TP           : 153 | 158
• RR Tactical  : 1.75
• RR Structural: 1.45

7. Trade Management
• Jika harga naik 5.00%, geser SL ke BEP.
• Jika TP1 tercapai, ambil partial profit 50%.
• Sisa posisi diarahkan ke TP2.
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
- breakout buffer
- pullback expiry
- market filter IHSG
- trade management
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
