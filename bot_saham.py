import yfinance as yf
import pandas as pd
import pandas_ta as ta
from google import genai
import requests
import os
from datetime import datetime
import time

# ==========================================
# KONFIGURASI API (Environment Variables)
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Inisialisasi Gemini Client
client = genai.Client(api_key=GEMINI_API_KEY)

def get_safe_value(row, prefix):
    """Mencari nilai indikator berdasarkan awalan."""
    for col in row.index:
        if str(col).startswith(prefix):
            val = row[col]
            return round(float(val), 2) if pd.notna(val) else 0
    return 0

def get_technical_data(ticker):
    """Mengambil data pasar dan menghitung indikator teknikal."""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1y")
        
        if df.empty:
            return None

        # Fix MultiIndex yfinance
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [str(col) for col in df.columns]

        # Kalkulasi Indikator
        df.ta.sma(length=10, append=True)
        df.ta.sma(length=20, append=True)
        df.ta.sma(length=50, append=True)
        df.ta.sma(length=200, append=True)
        df.ta.rsi(length=14, append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        df.ta.bbands(length=20, std=2, append=True)
        df['VOL_SMA_20'] = df['Volume'].rolling(window=20).mean()
        df.ta.mfi(length=14, append=True)

        last_60_days = df.tail(60)
        resistance = last_60_days['High'].max()
        support = last_60_days['Low'].min()
        latest = df.iloc[-1]

        phase = "Sideways / Konsolidasi 🟡"
        sma10 = get_safe_value(latest, 'SMA_10')
        sma50 = get_safe_value(latest, 'SMA_50')
        vol = float(latest['Volume']) if pd.notna(latest['Volume']) else 0
        vol_sma20 = float(latest['VOL_SMA_20']) if pd.notna(latest['VOL_SMA_20']) else 0

        if sma10 > sma50 and vol > vol_sma20:
            phase = "Akumulasi / Markup (Bullish) 🟢"
        elif sma10 < sma50 and vol > vol_sma20:
            phase = "Distribusi / Markdown (Bearish) 🔴"

        data_summary = {
            "Ticker": ticker,
            "Close Price": round(float(latest['Close']), 2),
            "MA10": sma10,
            "MA20": get_safe_value(latest, 'SMA_20'),
            "MA50": sma50,
            "MA200": get_safe_value(latest, 'SMA_200'),
            "RSI_14": get_safe_value(latest, 'RSI_14'),
            "MACD": get_safe_value(latest, 'MACD_'),
            "MACD_Signal": get_safe_value(latest, 'MACDs_'),
            "BB_Upper": get_safe_value(latest, 'BBU_'),
            "BB_Lower": get_safe_value(latest, 'BBL_'),
            "Volume": int(vol),
            "Volume_SMA_20": int(vol_sma20),
            "MFI_14": get_safe_value(latest, 'MFI_14'),
            "Support_3M": round(float(support), 2),
            "Resistance_3M": round(float(resistance), 2),
            "Market_Phase": phase
        }
        return data_summary

    except Exception as e:
        print(f"Error teknikal {ticker}: {e}")
        return None

def generate_with_openrouter(prompt):
    """Fungsi spesifik untuk memanggil API OpenRouter (Model Llama 3.1 Free)."""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        raise Exception(f"Error {response.status_code}: {response.text}")

def generate_ai_report(data):
    """Sistem Auto-Failover: Coba Gemini, jika limit/gagal, gunakan OpenRouter."""
    prompt = f"""
    Bertindaklah sebagai Senior Technical Analyst. Interpretasikan data teknikal berikut menjadi laporan narasi harian untuk trader profesional.
    
    DATA SAHAM:
    {data}

    INSTRUKSI OUTPUT:
    Gunakan gaya bahasa profesional, tajam, informatif, dan langsung pada intinya. 
    Output WAJIB menggunakan Markdown agar rapi saat dikirim ke Telegram.
    Gunakan emoji yang sesuai untuk memberikan penekanan visual (📈, 🟢, 🟡, 🔴, 🧱, 🧭, 🛡️).
    
    Struktur laporan HARUS mencakup 10 poin berikut secara berurutan:
    1. Tren Utama (Analisis singkat berdasarkan MA dan Fase)
    2. Moving Average (Posisinya terhadap MA pendek vs panjang)
    3. Momentum (Interpretasi RSI, MACD, dan Bollinger Bands)
    4. Volume (Bandingkan volume hari ini dengan rata-rata 20 hari)
    5. MFI (Money Flow Index - apakah ada indikasi smart money masuk/keluar)
    6. Support & Resistance (Sebutkan angka pastinya: Support {data['Support_3M']} dan Resistance {data['Resistance_3M']})
    7. Skenario Harga (Potensi pergerakan 1-3 hari ke depan)
    8. Strategi Entry (Berikan rekomendasi praktis: BoW, Breakout, atau Agresif)
    9. Manajemen Risiko (Di mana level Cut Loss ideal)
    10. Kesimpulan (Ringkasan eksekutif 1 kalimat)

    Tutup laporan dengan baris persis seperti ini:
    *Disclaimer: Keputusan investasi berada di tangan Anda. Do Your Own Research (DYOR).* 🛡️
    """
    
    # 1. Coba menggunakan Gemini API (Primary)
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
        )
        return f"💡 **[Report by Gemini AI]**\n\n{response.text}"
        
    except Exception as e:
        print(f"⚠️ Gemini Limit/Error ({e}). Beralih ke OpenRouter...")
        
        # 2. Jika Gemini gagal, gunakan OpenRouter API (Backup)
        if not OPENROUTER_API_KEY:
            return f"Maaf, Gemini gagal dan OpenRouter API Key belum dikonfigurasi untuk {data['Ticker']}."
            
        try:
            backup_response = generate_with_openrouter(prompt)
            return f"💡 **[Report by OpenRouter Llama 3.1]**\n\n{backup_response}"
        except Exception as ex:
            print(f"❌ OpenRouter juga gagal: {ex}")
            return f"Maaf, seluruh sistem AI sedang down saat memproses {data['Ticker']}."

def send_telegram_message(message):
    """Mengirim pesan laporan ke Telegram."""
    if not message: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def main():
    print(f"--- Memulai Rutinitas Analisis: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    file_path = "saham_pantauan.txt"
    
    if not os.path.exists(file_path): 
        print(f"File {file_path} tidak ditemukan.")
        return

    with open(file_path, "r") as f:
        raw_tickers = [line.strip().upper() for line in f if line.strip()]
        tickers = [t if t.endswith(".JK") else t + ".JK" for t in raw_tickers]

    for ticker in tickers:
        print(f"Menganalisis {ticker}...")
        tech_data = get_technical_data(ticker)
        
        if tech_data:
            report = generate_ai_report(tech_data)
            send_telegram_message(report)
            print(f"✅ Laporan {ticker} terkirim.")
        else:
            print(f"❌ Gagal mendapatkan data untuk {ticker}")

        # Jeda 30 detik untuk menghindari limit harian / Token Per Minute
        print("Menunggu 30 detik sebelum lanjut...")
        time.sleep(30)

    print("--- Semua tugas selesai ---")

if __name__ == "__main__":
    main()
