# 📈 IDX Technical Analyst Hybrid Engine

![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python)
![Pandas TA](https://img.shields.io/badge/Pandas_TA-Technical_Engine-success?style=for-the-badge)
![Gemini AI](https://img.shields.io/badge/Google%20Gemini-Primary_AI-orange?style=for-the-badge&logo=google)
![OpenRouter](https://img.shields.io/badge/Llama_3.3-Fallback_AI-black?style=for-the-badge&logo=meta)
![Telegram API](https://img.shields.io/badge/Telegram-Bot-informational?style=for-the-badge&logo=telegram)

**IDX Technical Analyst Hybrid Engine** adalah bot analitik otomatis yang mengintegrasikan data pasar saham Indonesia (IHSG) dengan perhitungan indikator teknikal tingkat lanjut.

Versi terbaru ini menggunakan arsitektur **Hybrid Deterministic**, di mana **Python Rule-Based Engine** memegang kendali utama atas logika analisis teknikal dan skenario trading, sementara AI (Gemini & Llama 3.3) bertindak sebagai asisten pemberi opini tambahan (*Insight*). Arsitektur ini menjaga *uptime* tetap tinggi meskipun layanan AI sedang mengalami *down* atau *rate limit*.

---

## 🏛️ Arsitektur Sistem (Fault-Tolerant)

Sistem ini dirancang anti-gagal dengan alur kerja berikut:

1. **Data Ingestion (Bulletproof):** `yfinance` mengambil data pasar (OHLCV). Sistem menangani *MultiIndex handling* secara otomatis dan melakukan *auto-append* `.JK`.
2. **Deterministic Engine:** `pandas_ta` dan Python menghitung MA, RSI, MACD, Volume, MFI, serta membentuk support, resistance, skenario harga, strategi entry, dan cut loss.
3. **AI Insight (Auto-Failover):**
   - Sistem meminta opini psikologis market singkat dari **Gemini**.
   - Jika Gemini gagal atau terkena limit, sistem otomatis beralih ke **OpenRouter (Meta Llama 3.3 70B)**.
   - Jika seluruh AI gagal, bot tetap mengirim laporan teknikal utama ke Telegram tanpa hambatan.
4. **Delivery:** Dieksekusi otomatis via **GitHub Actions** (*Cron Job*) setiap hari pukul 08:00 WIB.

---

## 📋 Prasyarat (*Prerequisites*)

- Akun **Google AI Studio** untuk `GEMINI_API_KEY`
- Akun **OpenRouter** untuk `OPENROUTER_API_KEY`
- Akun Telegram dan token bot dari **@BotFather** (`TELEGRAM_BOT_TOKEN`)
- ID chat atau channel Telegram (`TELEGRAM_CHAT_ID`)

---

## 🚀 Panduan Instalasi (Lokal)

### 1. Kloning Repositori

```bash
git clone https://github.com/USERNAME_ANDA/IDX-Technical-Analyst-Hybrid-Engine.git
cd IDX-Technical-Analyst-Hybrid-Engine
