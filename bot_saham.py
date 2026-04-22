import os
import re
import time
import math
from pathlib import Path
from datetime import datetime

import requests
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from pypdf import PdfReader

try:
    from google import genai
except Exception:
    genai = None


# =========================================================
# KONFIGURASI ENV
# =========================================================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

RUN_MODE = os.environ.get("RUN_MODE", "watchlist").strip().lower()  # watchlist | screener_syariah | hybrid
AI_PROVIDER = os.environ.get("AI_PROVIDER", "off").strip().lower()   # off | gemini | openrouter

WATCHLIST_FILE = os.environ.get("WATCHLIST_FILE", str(DATA_DIR / "saham_pantauan.txt"))
SYARIAH_UNIVERSE_FILE = os.environ.get("SYARIAH_UNIVERSE_FILE", str(DATA_DIR / "syariah_stocks.txt"))
SYARIAH_MASTER_FILE = os.environ.get("SYARIAH_MASTER_FILE", str(DATA_DIR / "syariah_stocks_master.txt"))
DES_PDF_LOCAL = os.environ.get("DES_PDF_LOCAL", str(DATA_DIR / "des_syariah_latest.pdf"))
DES_PDF_URL = os.environ.get(
    "DES_PDF_URL",
    "https://ojk.go.id/id/kanal/syariah/data-dan-statistik/daftar-efek-syariah/Documents/Pages/Daftar-Efek-Syariah-KEP59D042025/SK%20DES%20Periode%20II%202025%20%28Lampiran%20I%29.pdf"
)

SCREENER_LIMIT = int(os.environ.get("SCREENER_LIMIT", "5"))
SCREENER_PERIOD = os.environ.get("SCREENER_PERIOD", "6mo")
SCREENER_INTERVAL = os.environ.get("SCREENER_INTERVAL", "1d")
SCREENER_MAX_PRICE = float(os.environ.get("SCREENER_MAX_PRICE", "500"))
SCREENER_MIN_VOLUME_RATIO = float(os.environ.get("SCREENER_MIN_VOLUME_RATIO", "1.5"))
SCREENER_MIN_VALUE_TRADED = float(os.environ.get("SCREENER_MIN_VALUE_TRADED", "1000000000"))
SCREENER_MIN_RSI = float(os.environ.get("SCREENER_MIN_RSI", "55"))
SCREENER_BATCH_SIZE = int(os.environ.get("SCREENER_BATCH_SIZE", "40"))
SCREENER_DELAY_SECONDS = float(os.environ.get("SCREENER_DELAY_SECONDS", "1.0"))
SCREENER_ENABLE_AUTO_UPDATE_UNIVERSE = os.environ.get("SCREENER_ENABLE_AUTO_UPDATE_UNIVERSE", "1").strip() == "1"

# tambahan / pengecualian universe
INCIDENTAL_ADDITIONS = [x.strip().upper() for x in os.environ.get("INCIDENTAL_ADDITIONS", "BSAI").split(",") if x.strip()]
EXCLUDED_CODES = {x.strip().upper() for x in os.environ.get("EXCLUDED_CODES", "ALDI,BRAU,CPDW,INSA,MASA,RINA,SIMM,SING,SQBB,TRUE").split(",") if x.strip()}

# toggle report
ENABLE_AI_INSIGHT = os.environ.get("ENABLE_AI_INSIGHT", "0").strip() == "1"
TELEGRAM_PREFIX = os.environ.get("TELEGRAM_PREFIX", "").strip()

# client AI
GEMINI_CLIENT = None
if genai is not None and GEMINI_API_KEY:
    try:
        GEMINI_CLIENT = genai.Client(api_key=GEMINI_API_KEY)
    except Exception:
        GEMINI_CLIENT = None


# =========================================================
# HELPER UMUM
# =========================================================
def log(msg: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {msg}")


def normalize_ticker(code: str) -> str:
    code = str(code).strip().upper()
    if not code:
        return ""
    return code if code.endswith(".JK") else f"{code}.JK"


def denormalize_ticker(code: str) -> str:
    return str(code).strip().upper().replace(".JK", "")


def get_safe_value(row, prefix):
    """Ambil indikator berdasarkan prefix nama kolom."""
    for col in row.index:
        if str(col).startswith(prefix):
            val = row[col]
            return round(float(val), 2) if pd.notna(val) else 0
    return 0


def format_price(value):
    try:
        value = float(value)
        if value >= 100:
            return str(int(round(value)))
        return f"{value:.2f}"
    except Exception:
        return str(value)


def format_big_number(value):
    try:
        value = float(value)
    except Exception:
        return str(value)

    abs_val = abs(value)
    if abs_val >= 1_000_000_000_000:
        return f"{value / 1_000_000_000_000:.2f}T"
    if abs_val >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    if abs_val >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if abs_val >= 1_000:
        return f"{value / 1_000:.2f}K"
    return f"{value:.0f}"


def chunk_message(text: str, limit: int = 3900):
    text = str(text or "")
    if len(text) <= limit:
        return [text]

    chunks = []
    current = ""
    for line in text.splitlines(True):
        if len(current) + len(line) > limit:
            if current:
                chunks.append(current.rstrip())
            current = line
        else:
            current += line

    if current.strip():
        chunks.append(current.rstrip())

    return chunks or [""]


def send_to_telegram(message: str):
    message = str(message or "").strip()
    if TELEGRAM_PREFIX:
        message = f"{TELEGRAM_PREFIX}\n{message}"

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log("Telegram tidak aktif. Pesan ditampilkan ke console.")
        print(message)
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    for part in chunk_message(message):
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": part,
            "disable_web_page_preview": True,
        }
        try:
            resp = requests.post(url, data=payload, timeout=30)
            if resp.status_code != 200:
                log(f"Gagal kirim Telegram: {resp.status_code} - {resp.text}")
        except Exception as e:
            log(f"Error Telegram: {e}")


def unique_sorted_levels(levels, reverse=False, min_gap_ratio=0.02):
    """Rapikan level support/resistance agar tidak terlalu berdekatan."""
    clean = []
    for x in levels:
        try:
            x = float(x)
            if x <= 0:
                continue
            clean.append(x)
        except Exception:
            continue

    clean = sorted(clean, reverse=reverse)
    result = []
    for lv in clean:
        if not result:
            result.append(lv)
        else:
            if abs(lv - result[-1]) / result[-1] >= min_gap_ratio:
                result.append(lv)
    return result


def read_lines_file(path: str):
    fp = Path(path)
    if not fp.exists():
        return []
    items = []
    with open(fp, "r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if not raw or raw.startswith("#"):
                continue
            items.append(raw)
    return items


def write_lines_file(path: str, items, header=None):
    fp = Path(path)
    fp.parent.mkdir(parents=True, exist_ok=True)
    with open(fp, "w", encoding="utf-8") as f:
        if header:
            f.write(header.rstrip() + "\n")
        for item in items:
            f.write(f"{item}\n")


# =========================================================
# UNIVERSE SAHAM SYARIAH (AUTO UPDATE OJK PDF)
# =========================================================
def download_des_pdf(url: str, output_path: str):
    log(f"Download PDF DES: {url}")
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    Path(output_path).write_bytes(resp.content)
    log(f"PDF DES tersimpan: {output_path}")


def extract_text_from_pdf(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    texts = []
    for page in reader.pages:
        try:
            texts.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(texts)


def extract_stock_codes_from_des_text(text: str):
    """
    Ambil ticker dari pola tabel OJK, contoh:
    8 AADI PT Adaro Andalan Indonesia Tbk
    639 TLKM PT Telkom Indonesia (Persero) Tbk
    """
    codes = set()

    for raw_line in text.splitlines():
        line = " ".join(raw_line.strip().split())
        m = re.match(r"^\d+\s+([A-Z]{4,5})\s+PT\b", line)
        if m:
            codes.add(m.group(1))

    return sorted(codes)


def update_syariah_universe(force_download=False):
    """
    Update universe saham syariah dari PDF OJK.
    Jika download gagal, pakai file lama yang sudah ada.
    """
    master_path = str(Path(SYARIAH_MASTER_FILE))
    screener_path = str(Path(SYARIAH_UNIVERSE_FILE))
    pdf_path = str(Path(DES_PDF_LOCAL))

    pdf_exists = Path(pdf_path).exists()

    if force_download or not pdf_exists:
        try:
            download_des_pdf(DES_PDF_URL, pdf_path)
            pdf_exists = True
        except Exception as e:
            log(f"Gagal download PDF DES: {e}")

    extracted_codes = []
    if pdf_exists:
        try:
            text = extract_text_from_pdf(pdf_path)
            extracted_codes = extract_stock_codes_from_des_text(text)
            log(f"Kode terdeteksi dari PDF DES: {len(extracted_codes)}")
        except Exception as e:
            log(f"Gagal ekstrak PDF DES: {e}")

    if not extracted_codes:
        # fallback ke master file lama kalau ada
        old_master = [x.strip().upper() for x in read_lines_file(master_path)]
        if old_master:
            extracted_codes = old_master
            log(f"Menggunakan master lama: {len(extracted_codes)} kode")

    if not extracted_codes:
        raise RuntimeError("Universe syariah gagal dibentuk: PDF gagal diparsing dan file lama tidak tersedia.")

    master_codes = sorted(set(extracted_codes + INCIDENTAL_ADDITIONS))
    screener_codes = sorted(code for code in master_codes if code not in EXCLUDED_CODES)

    write_lines_file(
        master_path,
        master_codes,
        header=(
            "# Master saham syariah dari DES OJK + tambahan insidentil manual\n"
            f"# Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
    )

    write_lines_file(
        screener_path,
        screener_codes,
        header=(
            "# Universe saham syariah untuk screener yfinance\n"
            f"# Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
    )

    log(f"Master universe tersimpan: {master_path} ({len(master_codes)} kode)")
    log(f"Screener universe tersimpan: {screener_path} ({len(screener_codes)} kode)")
    return master_codes, screener_codes


def load_syariah_universe():
    fp = Path(SYARIAH_UNIVERSE_FILE)
    if not fp.exists():
        if SCREENER_ENABLE_AUTO_UPDATE_UNIVERSE:
            update_syariah_universe(force_download=False)
        else:
            raise FileNotFoundError(f"File universe syariah tidak ditemukan: {fp}")

    items = [normalize_ticker(x) for x in read_lines_file(str(fp))]
    items = sorted(set([x for x in items if x]))
    if not items:
        raise RuntimeError("File universe syariah kosong.")
    return items


# =========================================================
# WATCHLIST MANUAL
# =========================================================
def load_watchlist():
    fp = Path(WATCHLIST_FILE)
    if not fp.exists():
        legacy = BASE_DIR / "saham_pantauan.txt"
        if legacy.exists():
            fp = legacy
        else:
            return []

    items = [normalize_ticker(x) for x in read_lines_file(str(fp))]
    return sorted(set([x for x in items if x]))


# =========================================================
# TEKNIKAL
# =========================================================
def get_price_structure(df):
    """Deteksi struktur harga sederhana."""
    if len(df) < 12:
        return "Struktur belum cukup", "Netral"

    prev_block = df.iloc[-10:-5]
    curr_block = df.iloc[-5:]

    prev_high = prev_block["High"].max()
    prev_low = prev_block["Low"].min()
    curr_high = curr_block["High"].max()
    curr_low = curr_block["Low"].min()

    if curr_high > prev_high and curr_low > prev_low:
        return "mulai membentuk higher high & higher low", "bullish"
    elif curr_high < prev_high and curr_low < prev_low:
        return "masih membentuk lower high & lower low", "bearish"
    elif curr_high > prev_high and curr_low <= prev_low:
        return "higher high muncul, tapi higher low belum solid", "reversal"
    elif curr_high <= prev_high and curr_low > prev_low:
        return "higher low mulai muncul, reversal sedang dibangun", "reversal"
    else:
        return "masih sideways / struktur campuran", "netral"


def detect_market_phase(data):
    ma10 = data["MA10"]
    ma20 = data["MA20"]
    ma50 = data["MA50"]
    ma200 = data["MA200"]
    close = data["Close Price"]
    vol = data["Volume"]
    vol_sma20 = data["Volume_SMA_20"]
    rsi = data["RSI_14"]

    if close > ma10 > ma20 > ma50 > ma200:
        return "Markup"
    elif close > ma10 > ma20 > ma50 and vol > vol_sma20:
        return "Akumulasi → Markup"
    elif close < ma10 < ma20 < ma50 < ma200:
        return "Markdown"
    elif ma10 < ma50 and close > ma10 and vol > vol_sma20 and rsi > 50:
        return "Akumulasi"
    else:
        return "Sideways / Konsolidasi"


def get_support_resistance_levels(df, close_price):
    """
    Ambil 3 support dan 3 resistance dari:
    - Pivot
    - Swing 3 bulan
    - SMA20 / SMA50 / SMA200
    - Bollinger band
    """
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else df.iloc[-1]
    last_63 = df.tail(63)

    prev_high = float(prev["High"])
    prev_low = float(prev["Low"])
    prev_close = float(prev["Close"])

    pivot = (prev_high + prev_low + prev_close) / 3
    s1 = (2 * pivot) - prev_high
    r1 = (2 * pivot) - prev_low
    s2 = pivot - (prev_high - prev_low)
    r2 = pivot + (prev_high - prev_low)

    swing_low = float(last_63["Low"].min())
    swing_high = float(last_63["High"].max())

    ma20 = get_safe_value(last, "SMA_20")
    ma50 = get_safe_value(last, "SMA_50")
    ma200 = get_safe_value(last, "SMA_200")
    bb_upper = get_safe_value(last, "BBU_")
    bb_lower = get_safe_value(last, "BBL_")

    support_candidates = [s1, s2, swing_low, ma20, ma50, ma200, bb_lower]
    resistance_candidates = [r1, r2, swing_high, ma20, ma50, ma200, bb_upper]

    supports = [x for x in support_candidates if x < close_price]
    resistances = [x for x in resistance_candidates if x > close_price]

    supports = unique_sorted_levels(supports, reverse=True)
    resistances = unique_sorted_levels(resistances, reverse=False)

    while len(supports) < 3:
        if supports:
            supports.append(supports[-1] * 0.93)
        else:
            supports.append(close_price * 0.95)

    while len(resistances) < 3:
        if resistances:
            resistances.append(resistances[-1] * 1.07)
        else:
            resistances.append(close_price * 1.05)

    return {
        "support_1": round(supports[0], 2),
        "support_2": round(supports[1], 2),
        "support_3": round(supports[2], 2),
        "resistance_1": round(resistances[0], 2),
        "resistance_2": round(resistances[1], 2),
        "resistance_3": round(resistances[2], 2),
    }


def get_technical_data(ticker):
    """Ambil data pasar dan hitung indikator teknikal."""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1y", interval="1d", auto_adjust=False)

        if df.empty:
            return None

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
        df.ta.mfi(length=14, append=True)

        df["VOL_SMA_20"] = df["Volume"].rolling(window=20).mean()
        df = df.dropna().copy()

        if df.empty or len(df) < 30:
            return None

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        close_price = round(float(latest["Close"]), 2)
        volume = float(latest["Volume"]) if pd.notna(latest["Volume"]) else 0
        vol_sma20 = float(latest["VOL_SMA_20"]) if pd.notna(latest["VOL_SMA_20"]) else 0

        ma10 = get_safe_value(latest, "SMA_10")
        ma20 = get_safe_value(latest, "SMA_20")
        ma50 = get_safe_value(latest, "SMA_50")
        ma200 = get_safe_value(latest, "SMA_200")

        rsi14 = get_safe_value(latest, "RSI_14")
        macd_val = get_safe_value(latest, "MACD_")
        macd_signal = get_safe_value(latest, "MACDs_")
        macd_hist = get_safe_value(latest, "MACDh_")
        prev_macd_hist = get_safe_value(prev, "MACDh_")

        bb_upper = get_safe_value(latest, "BBU_")
        bb_lower = get_safe_value(latest, "BBL_")
        mfi14 = get_safe_value(latest, "MFI_14")

        price_structure, structure_flag = get_price_structure(df)
        sr_levels = get_support_resistance_levels(df, close_price)

        market_phase = detect_market_phase({
            "MA10": ma10,
            "MA20": ma20,
            "MA50": ma50,
            "MA200": ma200,
            "Close Price": close_price,
            "Volume": volume,
            "Volume_SMA_20": vol_sma20,
            "RSI_14": rsi14
        })

        prev_20_high = float(df["High"].iloc[-21:-1].max()) if len(df) >= 21 else float(df["High"].max())
        breakout_valid = close_price > prev_20_high and volume > vol_sma20

        data_summary = {
            "Ticker": ticker,
            "Close Price": close_price,
            "MA10": ma10,
            "MA20": ma20,
            "MA50": ma50,
            "MA200": ma200,
            "RSI_14": rsi14,
            "MACD": macd_val,
            "MACD_Signal": macd_signal,
            "MACD_Hist": macd_hist,
            "Prev_MACD_Hist": prev_macd_hist,
            "BB_Upper": bb_upper,
            "BB_Lower": bb_lower,
            "Volume": int(volume),
            "Volume_SMA_20": int(vol_sma20),
            "MFI_14": mfi14,
            "Market_Phase": market_phase,
            "Price_Structure": price_structure,
            "Structure_Flag": structure_flag,
            "Breakout_Valid": breakout_valid,
            **sr_levels
        }
        return data_summary

    except Exception as e:
        log(f"Error teknikal {ticker}: {e}")
        return None


# =========================================================
# REPORT RULE-BASED
# =========================================================
def generate_python_logic_report(data):
    close = data["Close Price"]
    ma10 = data["MA10"]
    ma20 = data["MA20"]
    ma50 = data["MA50"]
    ma200 = data["MA200"]
    rsi = data["RSI_14"]
    macd = data["MACD"]
    macd_signal = data["MACD_Signal"]
    macd_hist = data["MACD_Hist"]
    prev_macd_hist = data["Prev_MACD_Hist"]
    bb_upper = data["BB_Upper"]
    bb_lower = data["BB_Lower"]
    volume = data["Volume"]
    vol_sma20 = data["Volume_SMA_20"]
    mfi = data["MFI_14"]

    s1 = data["support_1"]
    s2 = data["support_2"]
    s3 = data["support_3"]
    r1 = data["resistance_1"]
    r2 = data["resistance_2"]
    r3 = data["resistance_3"]

    # 1. Tren utama
    if close > ma20 > ma50 > ma200 and data["Structure_Flag"] == "bullish":
        trend_condition = "Uptrend kuat"
        trend_bias = "Bullish kuat"
    elif ma50 < ma200 and close > ma20 and data["Structure_Flag"] in ["bullish", "reversal"]:
        trend_condition = "Downtrend → reversal kuat"
        trend_bias = "Bullish kuat"
    elif close < ma20 < ma50 < ma200 and data["Structure_Flag"] == "bearish":
        trend_condition = "Downtrend"
        trend_bias = "Bearish kuat"
    else:
        trend_condition = "Sideways / transisi"
        trend_bias = "Netral"

    breakout_note = "Terjadi breakout signifikan dari area konsolidasi" if data["Breakout_Valid"] else "Belum ada breakout signifikan"
    phase_text = data["Market_Phase"]

    # 2. MA
    if close > ma10 and close > ma20 and close > ma50:
        ma_position = "Di atas MA pendek, menengah & panjang"
    elif close > ma10 and close > ma20:
        ma_position = "Di atas MA pendek & menengah, tapi belum dominan di MA panjang"
    elif close < ma10 and close < ma20 and close < ma50:
        ma_position = "Di bawah MA pendek, menengah & panjang"
    else:
        ma_position = "Posisi harga campuran terhadap MA"

    if ma10 > ma20 > ma50:
        ma_order = "MA pendek > MA menengah > MA panjang"
        ma_structure = "Struktur bullish kuat"
    elif ma10 < ma20 < ma50:
        ma_order = "MA pendek < MA menengah < MA panjang"
        ma_structure = "Struktur bearish dominan"
    else:
        ma_order = "Susunan MA masih campuran"
        ma_structure = "Belum ada struktur dominan"

    # 3. Momentum
    if close > bb_upper:
        bb_text = "Harga menembus upper band"
        bb_signal = "Momentum sangat kuat"
    elif close < bb_lower:
        bb_text = "Harga menembus lower band"
        bb_signal = "Tekanan jual sangat kuat"
    else:
        bb_text = "Harga masih bergerak di dalam Bollinger Band"
        bb_signal = "Momentum normal / belum ekstrem"

    if rsi >= 75:
        rsi_signal = f"RSI ±{round(rsi)} → bullish sangat kuat, rawan jenuh beli"
    elif rsi >= 60:
        rsi_signal = f"RSI ±{round(rsi)} → bullish"
    elif rsi <= 30:
        rsi_signal = f"RSI ±{round(rsi)} → oversold / potensi rebound"
    else:
        rsi_signal = f"RSI ±{round(rsi)} → netral"

    if macd > macd_signal and macd_hist > prev_macd_hist:
        macd_signal_text = "Golden cross + histogram melebar → sinyal kenaikan kuat"
    elif macd > macd_signal:
        macd_signal_text = "Golden cross → momentum bullish"
    elif macd < macd_signal and macd_hist < prev_macd_hist:
        macd_signal_text = "Dead cross + histogram melemah → tekanan turun kuat"
    else:
        macd_signal_text = "MACD campuran → belum ada momentum dominan"

    # 4. Volume
    if volume > vol_sma20 * 2:
        volume_signal = "Volume melonjak besar → ada akumulasi kuat / tenaga beli tinggi"
    elif volume > vol_sma20:
        volume_signal = "Volume di atas rata-rata → minat meningkat"
    else:
        volume_signal = "Volume normal / rendah → partisipasi belum besar"

    # 5. MFI
    if mfi >= 85:
        mfi_signal = f"MFI ±{round(mfi)} → aliran dana sangat tinggi, rawan profit taking"
    elif mfi >= 65:
        mfi_signal = f"MFI ±{round(mfi)} → aliran dana masuk kuat"
    elif mfi <= 20:
        mfi_signal = f"MFI ±{round(mfi)} → aliran dana sangat lemah, potensi technical rebound"
    else:
        mfi_signal = f"MFI ±{round(mfi)} → aliran dana moderat"

    # 6. Skenario trading
    tp1 = r1
    tp2 = r2
    tp3 = r3
    sl_agresif = s1
    sl_moderat = s2

    rr1 = round((tp1 - close) / max(close - sl_agresif, 0.01), 2) if close > sl_agresif else "-"
    rr2 = round((tp2 - close) / max(close - sl_agresif, 0.01), 2) if close > sl_agresif else "-"

    if trend_bias.startswith("Bullish"):
        entry_plan = f"Entry ideal saat pullback sehat di area {format_price(s1)}–{format_price(ma20)} atau buy on strength jika breakout valid di atas {format_price(r1)}."
        action_plan = "Fokus buy on weakness saat trend sehat, atau buy on breakout jika volume mendukung."
    elif trend_bias.startswith("Bearish"):
        entry_plan = "Belum ideal untuk entry agresif. Tunggu base baru / reversal valid."
        action_plan = "Defensif. Hindari kejar harga."
    else:
        entry_plan = f"Trading cepat di area support {format_price(s1)} dan resistance {format_price(r1)} sambil tunggu arah yang lebih jelas."
        action_plan = "Netral. Tunggu konfirmasi."

    report = f"""📊 ANALISIS TEKNIKAL — ${denormalize_ticker(data["Ticker"])} (Daily)

1. Tren Utama
• Kondisi : {trend_condition}
• Bias    : {trend_bias}
• Fase    : {phase_text}
• Struktur: {data["Price_Structure"]}
• Catatan : {breakout_note}

2. Moving Average
• Posisi harga : {ma_position}
• Susunan MA   : {ma_order}
• Struktur MA  : {ma_structure}

3. Momentum
• Bollinger : {bb_text} → {bb_signal}
• RSI       : {rsi_signal}
• MACD      : {macd_signal_text}

4. Volume & Dana
• Volume    : {format_big_number(volume)} vs avg20 {format_big_number(vol_sma20)}
• Sinyal    : {volume_signal}
• MFI       : {mfi_signal}

5. Support / Resistance
• Support   : {format_price(s1)} | {format_price(s2)} | {format_price(s3)}
• Resistance: {format_price(r1)} | {format_price(r2)} | {format_price(r3)}

6. Strategy
• Entry     : {entry_plan}
• TP        : TP1 {format_price(tp1)} | TP2 {format_price(tp2)} | TP3 {format_price(tp3)}
• SL        : Agresif {format_price(sl_agresif)} | Moderat {format_price(sl_moderat)}
• R:R       : ke TP1 ≈ {rr1} | ke TP2 ≈ {rr2}
• Aksi      : {action_plan}

7. Ringkasan
• Harga saat ini : {format_price(close)}
• Kesimpulan     : {trend_condition} dengan bias {trend_bias.lower()}. Perhatikan area {format_price(s1)}–{format_price(r1)} sebagai zona keputusan berikutnya.
"""
    return report.strip()


# =========================================================
# AI INSIGHT OPSIONAL
# =========================================================
def generate_ai_insight(data, python_report):
    if not ENABLE_AI_INSIGHT:
        return ""

    prompt = f"""
Anda adalah analis teknikal saham Indonesia.
Berdasarkan data berikut, buat insight singkat maksimal 6 poin.
Fokus: tren, momentum, risiko, entry, TP, SL.
Jangan ulangi semua isi report Python, cukup tambahkan insight bernilai.

Data:
{data}

Report Python:
{python_report}
""".strip()

    if AI_PROVIDER == "gemini":
        return generate_ai_insight_gemini(prompt)
    elif AI_PROVIDER == "openrouter":
        return generate_ai_insight_openrouter(prompt)
    return ""


def generate_ai_insight_gemini(prompt: str):
    if GEMINI_CLIENT is None:
        return ""
    try:
        resp = GEMINI_CLIENT.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        text = getattr(resp, "text", "") or ""
        return text.strip()
    except Exception as e:
        log(f"Gemini error: {e}")
        return ""


def generate_ai_insight_openrouter(prompt: str):
    if not OPENROUTER_API_KEY:
        return ""
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "openai/gpt-4.1-mini",
            "messages": [
                {"role": "system", "content": "Anda analis teknikal saham Indonesia. Jawab ringkas, jelas, praktis."},
                {"role": "user", "content": prompt}
            ]
        }
        resp = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log(f"OpenRouter error: {e}")
        return ""


# =========================================================
# SCREENER SYARIAH
# =========================================================
def _prepare_single_ticker_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.copy()
    df.columns = [str(c) for c in df.columns]

    required_cols = {"Open", "High", "Low", "Close", "Volume"}
    if not required_cols.issubset(set(df.columns)):
        return pd.DataFrame()

    df["SMA20"] = ta.sma(df["Close"], length=20)
    df["SMA50"] = ta.sma(df["Close"], length=50)
    df["RSI14"] = ta.rsi(df["Close"], length=14)

    macd = ta.macd(df["Close"], fast=12, slow=26, signal=9)
    if macd is None or macd.empty:
        return pd.DataFrame()

    df["MACD"] = macd["MACD_12_26_9"]
    df["MACD_SIGNAL"] = macd["MACDs_12_26_9"]
    df["MACD_HIST"] = macd["MACDh_12_26_9"]

    df["VOL_SMA20"] = df["Volume"].rolling(20).mean()
    df["RET_1D_PCT"] = df["Close"].pct_change() * 100
    df["VALUE_TRADED"] = df["Close"] * df["Volume"]
    df["HIGH_20"] = df["High"].rolling(20).max()
    df["LOW_20"] = df["Low"].rolling(20).min()
    df["SMA20_SLOPE_5"] = df["SMA20"].diff(5)

    df = df.dropna().copy()
    if len(df) < 60:
        return pd.DataFrame()

    return df


def _safe_float(value, default=0.0):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def _analyze_screener_row(ticker: str, df: pd.DataFrame):
    if df is None or df.empty:
        return None

    last = df.iloc[-1]
    prev = df.iloc[-2]

    close = _safe_float(last["Close"])
    prev_close = _safe_float(prev["Close"])
    volume = _safe_float(last["Volume"])
    vol_sma20 = _safe_float(last["VOL_SMA20"])
    ret_1d = _safe_float(last["RET_1D_PCT"])
    value_traded = _safe_float(last["VALUE_TRADED"])
    sma20 = _safe_float(last["SMA20"])
    sma50 = _safe_float(last["SMA50"])
    rsi14 = _safe_float(last["RSI14"])
    macd = _safe_float(last["MACD"])
    macd_signal = _safe_float(last["MACD_SIGNAL"])
    high_20 = _safe_float(last["HIGH_20"])
    low_20 = _safe_float(last["LOW_20"])
    sma20_slope_5 = _safe_float(last["SMA20_SLOPE_5"])

    if close <= 0 or vol_sma20 <= 0:
        return None

    volume_ratio = volume / vol_sma20 if vol_sma20 > 0 else 0.0
    distance_to_high_20_pct = ((close / high_20) - 1) * 100 if high_20 > 0 else 0.0
    rebound_from_low_20_pct = ((close / low_20) - 1) * 100 if low_20 > 0 else 0.0

    trend_ok = (
        close > sma20 and
        sma20 > sma50 and
        sma20_slope_5 > 0 and
        rsi14 >= SCREENER_MIN_RSI and
        macd > macd_signal
    )

    price_ok = close <= SCREENER_MAX_PRICE
    volume_ok = volume_ratio >= SCREENER_MIN_VOLUME_RATIO
    return_ok = ret_1d > 0
    liquidity_ok = value_traded >= SCREENER_MIN_VALUE_TRADED

    eligible = all([trend_ok, price_ok, volume_ok, return_ok, liquidity_ok])

    normalized_volume = min(volume_ratio, 3.0) / 3.0
    normalized_ret = min(max(ret_1d, 0.0), 10.0) / 10.0
    normalized_liquidity = min(value_traded / 10_000_000_000, 1.0)

    trend_strength = sum([
        close > sma20,
        sma20 > sma50,
        rsi14 >= SCREENER_MIN_RSI,
        macd > macd_signal,
        sma20_slope_5 > 0,
    ]) / 5.0

    breakout_proximity = min(close / high_20, 1.0) if high_20 > 0 else 0.0

    score = (
        normalized_volume * 35 +
        normalized_ret * 20 +
        trend_strength * 20 +
        breakout_proximity * 15 +
        normalized_liquidity * 10
    ) * 100

    return {
        "Ticker": denormalize_ticker(ticker),
        "Ticker_YF": ticker,
        "Close": round(close, 2),
        "Prev_Close": round(prev_close, 2),
        "Ret_1D_Pct": round(ret_1d, 2),
        "Volume": int(volume),
        "Vol_SMA20": int(vol_sma20),
        "Volume_Ratio": round(volume_ratio, 2),
        "Value_Traded": round(value_traded, 0),
        "SMA20": round(sma20, 2),
        "SMA50": round(sma50, 2),
        "RSI14": round(rsi14, 2),
        "MACD_Bullish": bool(macd > macd_signal),
        "Trend_OK": bool(trend_ok),
        "Price_OK": bool(price_ok),
        "Volume_OK": bool(volume_ok),
        "Return_OK": bool(return_ok),
        "Liquidity_OK": bool(liquidity_ok),
        "Eligible": bool(eligible),
        "Near_High_20_Pct": round(distance_to_high_20_pct, 2),
        "Rebound_From_Low_20_Pct": round(rebound_from_low_20_pct, 2),
        "Score": round(score, 2),
    }


def _download_batch(tickers):
    if not tickers:
        return pd.DataFrame()

    try:
        data = yf.download(
            tickers=tickers,
            period=SCREENER_PERIOD,
            interval=SCREENER_INTERVAL,
            auto_adjust=False,
            group_by="ticker",
            threads=True,
            progress=False,
        )
        return data
    except Exception as e:
        log(f"Batch download error: {e}")
        return pd.DataFrame()


def _extract_ticker_frame(batch_df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if batch_df is None or batch_df.empty:
        return pd.DataFrame()

    try:
        if isinstance(batch_df.columns, pd.MultiIndex):
            if ticker in batch_df.columns.get_level_values(0):
                return batch_df[ticker].copy()
            if ticker in batch_df.columns.get_level_values(1):
                return batch_df.xs(ticker, axis=1, level=1).copy()
        else:
            return batch_df.copy()
    except Exception:
        return pd.DataFrame()

    return pd.DataFrame()


def screen_syariah_stocks(limit=None):
    if limit is None:
        limit = SCREENER_LIMIT

    tickers = load_syariah_universe()
    all_rows = []

    for i in range(0, len(tickers), SCREENER_BATCH_SIZE):
        batch = tickers[i:i + SCREENER_BATCH_SIZE]
        log(f"Scanning batch {i+1}-{i+len(batch)} / {len(tickers)}")
        batch_df = _download_batch(batch)

        for ticker in batch:
            try:
                one_df = _extract_ticker_frame(batch_df, ticker)

                if one_df is None or one_df.empty:
                    one_df = yf.Ticker(ticker).history(
                        period=SCREENER_PERIOD,
                        interval=SCREENER_INTERVAL,
                        auto_adjust=False
                    )

                prepared = _prepare_single_ticker_frame(one_df)
                row = _analyze_screener_row(ticker, prepared)
                if row:
                    all_rows.append(row)

            except Exception as e:
                log(f"[SCREENER ERROR] {ticker}: {e}")

        if SCREENER_DELAY_SECONDS > 0:
            time.sleep(SCREENER_DELAY_SECONDS)

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)
    df = df[df["Eligible"] == True].copy()

    if df.empty:
        return df

    df = df.sort_values(
        by=["Score", "Volume_Ratio", "Ret_1D_Pct", "Value_Traded"],
        ascending=[False, False, False, False]
    ).head(limit).reset_index(drop=True)

    return df


def format_screener_telegram(df: pd.DataFrame, max_items: int = 10):
    if df is None or df.empty:
        return (
            "📌 Screener Saham Syariah Trending\n\n"
            "Tidak ada saham yang lolos filter hari ini.\n"
            "Filter aktif:\n"
            "• Harga ≤ 500\n"
            "• Volume > 1.5x rata-rata 20 hari\n"
            "• Return harian positif\n"
            "• Close > SMA20 > SMA50\n"
            "• RSI dan MACD bullish"
        )

    lines = [
        "📌 Screener Saham Syariah Trending",
        "",
        "Kriteria:",
        "• Harga ≤ 500",
        "• Volume > 1.5x rata-rata 20 hari",
        "• Return harian positif",
        "• Close > SMA20 > SMA50",
        "• RSI dan MACD bullish",
        "",
    ]

    max_items = min(max_items, len(df))

    for i in range(max_items):
        row = df.iloc[i]
        lines.extend([
            f"{i+1}. ${row['Ticker']}",
            f"   Harga     : {format_price(row['Close'])}",
            f"   Return 1D : {row['Ret_1D_Pct']}%",
            f"   Vol Ratio : {row['Volume_Ratio']}x",
            f"   Value     : {format_big_number(row['Value_Traded'])}",
            f"   RSI       : {row['RSI14']}",
            f"   Score     : {row['Score']}",
            ""
        ])

    return "\n".join(lines).strip()


# =========================================================
# RUNNERS
# =========================================================
def build_final_report(data):
    python_report = generate_python_logic_report(data)
    ai_text = generate_ai_insight(data, python_report)
    if ai_text:
        return f"{python_report}\n\n🧠 AI Insight:\n{ai_text}".strip()
    return python_report


def run_watchlist_mode():
    tickers = load_watchlist()
    if not tickers:
        send_to_telegram("❌ Watchlist kosong. Isi data/saham_pantauan.txt terlebih dahulu.")
        return

    send_to_telegram(
        f"🚀 Mode: WATCHLIST\n"
        f"Jumlah ticker: {len(tickers)}\n"
        f"Waktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    for ticker in tickers:
        log(f"[WATCHLIST] {ticker}")
        data = get_technical_data(ticker)
        if not data:
            send_to_telegram(f"⚠️ Gagal mengambil data untuk {ticker}")
            continue

        final_report = build_final_report(data)
        send_to_telegram(final_report)


def run_screener_syariah_mode():
    if SCREENER_ENABLE_AUTO_UPDATE_UNIVERSE:
        try:
            update_syariah_universe(force_download=False)
        except Exception as e:
            log(f"Auto update universe gagal, lanjut pakai file existing: {e}")

    screened_df = screen_syariah_stocks(limit=SCREENER_LIMIT)
    screener_text = format_screener_telegram(screened_df, max_items=SCREENER_LIMIT)
    send_to_telegram(screener_text)

    if screened_df is None or screened_df.empty:
        return

    for _, row in screened_df.iterrows():
        yf_ticker = normalize_ticker(row["Ticker"])
        log(f"[SCREENER] Analisa lanjutan {yf_ticker}")

        data = get_technical_data(yf_ticker)
        if not data:
            send_to_telegram(f"⚠️ Gagal mengambil data teknikal untuk {yf_ticker}")
            continue

        final_report = build_final_report(data)
        send_to_telegram(final_report)


def run_hybrid_mode():
    """
    Hybrid:
    1) jalankan screener syariah
    2) analisa kandidat screener
    3) analisa tambahan watchlist manual yang belum ter-cover
    """
    if SCREENER_ENABLE_AUTO_UPDATE_UNIVERSE:
        try:
            update_syariah_universe(force_download=False)
        except Exception as e:
            log(f"Auto update universe gagal, lanjut pakai file existing: {e}")

    screened_df = screen_syariah_stocks(limit=SCREENER_LIMIT)
    send_to_telegram(format_screener_telegram(screened_df, max_items=SCREENER_LIMIT))

    screened_tickers = set()
    if screened_df is not None and not screened_df.empty:
        screened_tickers = {normalize_ticker(x) for x in screened_df["Ticker"].tolist()}
        for yf_ticker in screened_tickers:
            log(f"[HYBRID-SCREENER] {yf_ticker}")
            data = get_technical_data(yf_ticker)
            if data:
                send_to_telegram(build_final_report(data))

    watchlist_tickers = load_watchlist()
    extra_watchlist = [x for x in watchlist_tickers if x not in screened_tickers]

    if extra_watchlist:
        send_to_telegram(
            f"📋 Tambahan analisa watchlist manual\n"
            f"Jumlah ticker tambahan: {len(extra_watchlist)}"
        )

    for ticker in extra_watchlist:
        log(f"[HYBRID-WATCHLIST] {ticker}")
        data = get_technical_data(ticker)
        if not data:
            send_to_telegram(f"⚠️ Gagal mengambil data untuk {ticker}")
            continue
        send_to_telegram(build_final_report(data))


# =========================================================
# MAIN
# =========================================================
def main():
    log(f"RUN_MODE = {RUN_MODE}")

    try:
        if RUN_MODE == "screener_syariah":
            run_screener_syariah_mode()
        elif RUN_MODE == "hybrid":
            run_hybrid_mode()
        else:
            run_watchlist_mode()
    except Exception as e:
        log(f"Fatal error: {e}")
        send_to_telegram(f"❌ Bot saham mengalami error fatal:\n{e}")


if __name__ == "__main__":
    main()