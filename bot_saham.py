import yfinance as yf
import pandas as pd
import pandas_ta as ta
from google import genai
import requests
import os
from datetime import datetime
import time

# ==========================================
# KONFIGURASI API
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

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
        
        if df.empty: return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [str(col) for col in df.columns]

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

        # Logika Fase Market Python
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

def generate_python_logic_report(data):
    """
    ENGINE UTAMA: Logika pengambilan keputusan dan pembuatan laporan murni 100% menggunakan Python.
    Tidak memerlukan API eksternal, uptime 100%.
    """
    # 1. Logika Trend
    trend_ma200 = "Bullish Jangka Panjang 🟢" if data['Close Price'] > data['MA200'] else "Bearish Jangka Panjang 🔴"
    
    # 2. Logika Momentum (RSI)
    if data['RSI_14'] >= 70:
        rsi_status = f"{data['RSI_14']} (Overbought 🔴 - Rawan Profit Taking)"
    elif data['RSI_14'] <= 30:
        rsi_status = f"{data['RSI_14']} (Oversold 🟢 - Potensi Technical Rebound)"
    else:
        rsi_status = f"{data['RSI_14']} (Netral 🟡)"

    # 3. Logika MACD
    if data['MACD'] > data['MACD_Signal']:
        macd_status = "Golden Cross / Bullish Momentum 🟢"
    else:
        macd_status = "Dead Cross / Bearish Momentum 🔴"

    # 4. Logika Volume
    if data['Volume'] > data['Volume_SMA_20']:
        vol_status = "Di atas rata-rata 20 hari 🟢 (Ada dorongan kuat)"
    else:
        vol_status = "Di bawah rata-rata 20 hari 🟡 (Sepi transaksi)"

    # 5. Logika Strategi Entry
    close = data['Close Price']
    if "Bullish" in data['Market_Phase'] and data['RSI_14'] < 70:
        strategi = "Trend Following. Tahan (Hold) atau Buy on Weakness di area MA20."
    elif "Bearish" in data['Market_Phase']:
        strategi = "Wait & See 🟡. Sangat berisiko, tunggu sinyal reversal jelas."
    elif close > data['Resistance_3M']:
        strategi = "Buy on Breakout 🚀 dengan volume konfirmasi."
    elif close < data['Support_3M']:
        strategi = "Hindari 🔴. Harga breakdown dari support kuat."
    else:
        strategi = "Trading Range 🧭. Buy dekat support, Sell dekat resistance."

    # Membangun Teks Laporan
    report = f"🏢 **ANALISIS TEKNIKAL: {data['Ticker']}**\n"
    report += f"Harga Terakhir: **{data['Close Price']}**\n\n"
    
    report += f"**1. Tren Utama:** {data['Market_Phase']}\n"
    report += f"**2. Siklus Panjang:** {trend_ma200}\n"
    report += f"**3. Momentum RSI:** {rsi_status}\n"
    report += f"**4. Momentum MACD:** {macd_status}\n"
    report += f"**5. Volume:** {vol_status}\n"
    report += f"**6. Support Kuat (3B):** {data['Support_3M']}\n"
    report += f"**7. Resistance (3B):** {data['Resistance_3M']}\n"
    report += f"**8. Strategi Dasar:** {strategi}\n"
    report += f"**9. Level Cut Loss:** Tembus di bawah {data['Support_3M']}\n"
    
    return report

def get_ai_insight(data):
    """
    ENGINE SEKUNDER: Hanya meminta 1 paragraf opini dari AI.
    Jika gagal, akan return string kosong dan tidak mengganggu laporan utama.
    """
    prompt = f"Berikan opini singkat (maks 2 kalimat) sebagai trader profesional untuk saham {data['Ticker']} berdasarkan data ini: Harga {data['Close Price']}, RSI {data['RSI_14']}, Fase: {data['Market_Phase']}. Jangan ulangi angkanya, fokus pada psikologi market."
    
    # Coba Gemini
    try:
        if client:
            response = client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
            return f"\n\n🤖 **AI Insight (Gemini):** {response.text.strip()}"
    except Exception:
        pass # Abaikan error Gemini

    # Coba OpenRouter (Llama 3.3) jika Gemini gagal
    try:
        if OPENROUTER_API_KEY:
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
            payload = {
                "model": "meta-llama/llama-3.3-70b-instruct:free",
                "messages": [{"role": "user", "content": prompt}]
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=10)
            if resp.status_code == 200:
                ai_text = resp.json()['choices'][0]['message']['content']
                return f"\n\n🤖 **AI Insight (Llama):** {ai_text.strip()}"
    except Exception:
        pass # Abaikan error OpenRouter

    # Jika semua AI gagal/limit, return kosong
    return ""

def send_telegram_message(message):
    if not message: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def main():
    print(f"--- Memulai Rutinitas Analisis: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    file_path = "saham_pantauan.txt"
    
    if not os.path.exists(file_path): return

    with open(file_path, "r") as f:
        tickers = [line.strip().upper() + ".JK" if not line.strip().upper().endswith(".JK") else line.strip().upper() for line in f if line.strip()]

    for ticker in tickers:
        print(f"Menganalisis {ticker}...")
        tech_data = get_technical_data(ticker)
        
        if tech_data:
            # 1. Buat Laporan Dasar dari Python (Pasti Berhasil)
            final_report = generate_python_logic_report(tech_data)
            
            # 2. Coba tambahkan opini AI (Opsional)
            ai_bonus = get_ai_insight(tech_data)
            final_report += ai_bonus
            
            # 3. Tambahkan Disclaimer
            final_report += "\n\n*Disclaimer: DYOR. Generated by Rule-Based Python Engine.* 🛡️"
            
            send_telegram_message(final_report)
            print(f"✅ Laporan {ticker} terkirim.")
        else:
            print(f"❌ Gagal mendapatkan data untuk {ticker}")

        time.sleep(5) # Jeda bisa diturunkan karena AI hanya minta token sangat sedikit

    print("--- Semua tugas selesai ---")

if __name__ == "__main__":
    main()