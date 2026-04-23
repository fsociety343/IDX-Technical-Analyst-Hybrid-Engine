# IDX Technical Analyst Hybrid Engine PRO v3 Feed

Versi ini menambahkan **feed JSON publik** agar hasil screener dari GitHub Actions bisa dibaca oleh web app seperti Trading Journal Pro.

## Tujuan integrasi

Bot mem-publish file:

`data/latest_screener.json`

Lalu GitHub Actions meng-commit file itu kembali ke branch `main`, sehingga bisa diakses dari raw GitHub URL.

Contoh URL feed:

`https://raw.githubusercontent.com/fsociety343/IDX-Technical-Analyst-Hybrid-Engine/main/data/latest_screener.json`

## File dalam paket ini

### `bot_saham_pro_v3_feed.py`
Versi bot PRO v3 yang menambahkan:
- `SCREENER_JSON_OUTPUT`
- `build_screener_feed_json()`
- `export_screener_json()`

Bot tetap mendukung:
- `RUN_MODE=watchlist/screener_syariah/hybrid`
- `TRADING_STYLE=swing/daytrade/scalping`

### `daily_report_pro_v3_feed.yml`
Workflow GitHub Actions yang:
- menjalankan bot
- menulis `data/latest_screener.json`
- commit feed JSON ke repo

### `README_pro_v3_feed.md`
Dokumentasi singkat integrasi feed publik.

## Struktur JSON

Format minimal feed:

```json
{
  "meta": {
    "generated_at": "2026-04-23T14:00:00Z",
    "source": "IDX Technical Analyst Hybrid Engine PRO v3 Feed",
    "run_mode": "hybrid",
    "trading_style": "swing",
    "style_label": "SWING",
    "screener_limit": 5,
    "screener_max_price": 100,
    "market_symbol": "^JKSE",
    "market_status": "Uptrend / mendukung",
    "market_ok": true,
    "feed_version": "1.0"
  },
  "summary": {
    "count": 3,
    "top_tickers": ["BUMI", "BNBR", "ZATA"]
  },
  "items": [
    {
      "ticker": "BUMI",
      "ticker_yf": "BUMI.JK",
      "price": 96,
      "return_1d_pct": 4.35,
      "volume_ratio": 2.14,
      "value_traded": 12400000000,
      "rsi14": 66.2,
      "score": 84.5,
      "eligible": true,
      "style": "swing"
    }
  ]
}
```

## Integrasi ke Trading Journal Pro

Isi `screener_feed_url` di web app dengan:

`https://raw.githubusercontent.com/fsociety343/IDX-Technical-Analyst-Hybrid-Engine/main/data/latest_screener.json`

## Langkah penggunaan

1. Replace `bot_saham.py` dengan `bot_saham_pro_v3_feed.py`
2. Replace workflow `.github/workflows/daily_report.yml` dengan `daily_report_pro_v3_feed.yml`
3. Pastikan repo punya file:
   - `data/saham_pantauan.txt`
   - `data/syariah_stocks.txt`
   - `data/syariah_stocks_master.txt`
   - `data/latest_screener.json`
4. Jalankan workflow
5. Ambil URL raw feed dan masukkan ke web app

## Catatan

- Telegram tetap dipakai untuk notifikasi.
- Feed JSON dipakai untuk integrasi sistem lain.
- Pendekatan ini paling sederhana dan cocok untuk repo GitHub publik.

## Update JSON Feed untuk Dashboard

Patch ini menyesuaikan output JSON agar lebih lengkap untuk dashboard screener web app.

## Field yang sekarang diisi

### `meta`
- `generated_at`
- `source`
- `run_mode`
- `trading_style`
- `style_label`
- `market_symbol`
- `market_status`
- `market_ok`

### `summary`
- `count`
- `top_tickers`
- `avg_rr`
- `avg_score`
- `buy_bullish_count`

### `items[]`
- `ticker`
- `name`
- `price`
- `last`
- `change_pct`
- `score`
- `signal`
- `strategy`
- `entry`
- `take_profit`
- `take_profit_1`
- `take_profit_2`
- `tp1`
- `tp2`
- `stop_loss`
- `sl`
- `rr`
- `volume_ratio`
- `vol_ratio`
- `value_traded`
- `value`
- `notes`
- `action_status`
- `setup_grade`
- `market_filter_ok`

Patch ini dibuat agar card dashboard seperti:
- Total Kandidat
- Avg RR
- Avg Score
- Buy/Bullish
- Generated At
- Run Mode
- Last / Entry / SL / TP1 / TP2 / RR / Vol Ratio / Value

bisa langsung diisi dari JSON.
