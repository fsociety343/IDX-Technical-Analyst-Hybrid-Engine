import os
import re
import time
import json
from pathlib import Path
from datetime import datetime, timezone

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
# STYLE CONFIG
# =========================================================
def get_style_config(style: str):
    style = (style or "swing").strip().lower()
    configs = {
        "swing": {
            "label": "SWING",
            "min_rr": 1.5,
            "max_stop_pct": 5.0,
            "breakout_buffer_pct": 0.01,
            "breakout_buffer_abs": 1.0,
            "pullback_expiry_days": 5,
            "tp1_mult": 1.05,
            "tp2_mult": 1.12,
            "move_bep_pct": 5.0,
            "partial_tp_pct": 50.0,
            "preferred_scenario": "pullback",
            "entry_ready_requires_market": True,
            "description": "Fokus pada follow trend dan pullback sehat untuk horizon beberapa hari sampai minggu.",
        },
        "daytrade": {
            "label": "DAYTRADE",
            "min_rr": 1.2,
            "max_stop_pct": 3.0,
            "breakout_buffer_pct": 0.006,
            "breakout_buffer_abs": 0.5,
            "pullback_expiry_days": 2,
            "tp1_mult": 1.03,
            "tp2_mult": 1.06,
            "move_bep_pct": 3.0,
            "partial_tp_pct": 50.0,
            "preferred_scenario": "breakout",
            "entry_ready_requires_market": True,
            "description": "Fokus pada momentum harian. Jangan menahan posisi terlalu lama jika trigger gagal lanjut.",
        },
        "scalping": {
            "label": "SCALPING",
            "min_rr": 1.0,
            "max_stop_pct": 2.0,
            "breakout_buffer_pct": 0.003,
            "breakout_buffer_abs": 0.3,
            "pullback_expiry_days": 1,
            "tp1_mult": 1.015,
            "tp2_mult": 1.03,
            "move_bep_pct": 2.0,
            "partial_tp_pct": 70.0,
            "preferred_scenario": "breakout",
            "entry_ready_requires_market": True,
            "description": "Fokus pada eksekusi cepat, target pendek, dan stop ketat. Jika tidak langsung bergerak, keluar.",
        },
    }
    return configs.get(style, configs["swing"])


# =========================================================
# KONFIGURASI ENV
# =========================================================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

TRADING_STYLE = os.environ.get("TRADING_STYLE", "swing").strip().lower()
STYLE_CONFIG = get_style_config(TRADING_STYLE)

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
SCREENER_MAX_PRICE = float(os.environ.get("SCREENER_MAX_PRICE", "100"))
SCREENER_MIN_VOLUME_RATIO = float(os.environ.get("SCREENER_MIN_VOLUME_RATIO", "1.5"))
SCREENER_MIN_VALUE_TRADED = float(os.environ.get("SCREENER_MIN_VALUE_TRADED", "1000000000"))
SCREENER_MIN_RSI = float(os.environ.get("SCREENER_MIN_RSI", "55"))
SCREENER_BATCH_SIZE = int(os.environ.get("SCREENER_BATCH_SIZE", "40"))
SCREENER_DELAY_SECONDS = float(os.environ.get("SCREENER_DELAY_SECONDS", "1.0"))
SCREENER_ENABLE_AUTO_UPDATE_UNIVERSE = os.environ.get("SCREENER_ENABLE_AUTO_UPDATE_UNIVERSE", "1").strip() == "1"
SCREENER_JSON_OUTPUT = os.environ.get("SCREENER_JSON_OUTPUT", str(DATA_DIR / "latest_screener.json"))

MIN_ACCEPTABLE_RR = float(os.environ.get("MIN_ACCEPTABLE_RR", str(STYLE_CONFIG["min_rr"])))
ACCOUNT_SIZE = float(os.environ.get("ACCOUNT_SIZE", "3000000"))
RISK_PER_TRADE_PCT = float(os.environ.get("RISK_PER_TRADE_PCT", "1"))
MAX_STOP_PCT = float(os.environ.get("MAX_STOP_PCT", str(STYLE_CONFIG["max_stop_pct"])))
MAX_STOP_DECIMAL = MAX_STOP_PCT / 100.0

BREAKOUT_BUFFER_PCT = float(os.environ.get("BREAKOUT_BUFFER_PCT", str(STYLE_CONFIG["breakout_buffer_pct"] * 100))) / 100.0
BREAKOUT_BUFFER_ABS = float(os.environ.get("BREAKOUT_BUFFER_ABS", str(STYLE_CONFIG["breakout_buffer_abs"])))
PULLBACK_EXPIRY_DAYS = int(os.environ.get("PULLBACK_EXPIRY_DAYS", str(STYLE_CONFIG["pullback_expiry_days"])))
USE_MARKET_FILTER = os.environ.get("USE_MARKET_FILTER", "1").strip() == "1"
MARKET_SYMBOL = os.environ.get("MARKET_SYMBOL", "^JKSE").strip()
MOVE_SL_TO_BEP_AT_PCT = float(os.environ.get("MOVE_SL_TO_BEP_AT_PCT", str(STYLE_CONFIG["move_bep_pct"])))
PARTIAL_TAKE_PROFIT_AT_TP1_PCT = float(os.environ.get("PARTIAL_TAKE_PROFIT_AT_TP1_PCT", str(STYLE_CONFIG["partial_tp_pct"])))

INCIDENTAL_ADDITIONS = [x.strip().upper() for x in os.environ.get("INCIDENTAL_ADDITIONS", "BSAI").split(",") if x.strip()]
EXCLUDED_CODES = {x.strip().upper() for x in os.environ.get("EXCLUDED_CODES", "ALDI,BRAU,CPDW,INSA,MASA,RINA,SIMM,SING,SQBB,TRUE").split(",") if x.strip()}

ENABLE_AI_INSIGHT = os.environ.get("ENABLE_AI_INSIGHT", "0").strip() == "1"
TELEGRAM_PREFIX = os.environ.get("TELEGRAM_PREFIX", "").strip()

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


def get_company_name(ticker_yf: str, fallback_ticker: str = "") -> str:
    try:
        info = yf.Ticker(ticker_yf).info
        name = info.get("longName") or info.get("shortName") or ""
        if name:
            return str(name).strip()
    except Exception:
        pass
    return fallback_ticker


def build_signal_and_strategy(meta: dict) -> tuple[str, str, str]:
    style = str(meta.get("style", TRADING_STYLE)).lower()
    action_status = str(meta.get("action_status", "WAIT FOR TRIGGER"))
    preferred_label = str(meta.get("preferred_label", "Pullback"))

    if action_status == "ENTRY READY":
        signal = "BUY"
    elif action_status == "WAIT FOR TRIGGER":
        signal = "WAIT"
    else:
        signal = "SKIP"

    if style == "scalping":
        strategy = "Scalping breakout" if preferred_label.lower() == "breakout" else "Scalping pullback"
    elif style == "daytrade":
        strategy = "Momentum continuation" if preferred_label.lower() == "breakout" else "Daytrade pullback"
    else:
        strategy = "Swing breakout" if preferred_label.lower() == "breakout" else "Swing pullback"

    notes = meta.get("notes_for_feed", "")
    return signal, strategy, notes


def get_safe_value(row, prefix):
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


def format_percent(value):
    try:
        return f"{float(value):.2f}%"
    except Exception:
        return str(value)


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


def calc_rr(entry, stop, target):
    risk = entry - stop
    reward = target - entry
    if risk <= 0 or reward <= 0:
        return 0.0
    return round(reward / risk, 2)


def rr_quality_label(rr_value):
    if rr_value >= 2:
        return "Sangat sehat"
    if rr_value >= 1.5:
        return "Sehat"
    if rr_value >= 1:
        return "Sedang"
    return "Kurang menarik"


def get_setup_grade(action_status, rr_best, breakout_confirmed, pullback_confirmed, market_ok):
    if action_status == "ENTRY READY":
        if market_ok and rr_best >= 2 and (breakout_confirmed or pullback_confirmed):
            return "A"
        if rr_best >= 1.5:
            return "B"
        return "C"
    if action_status == "WAIT FOR TRIGGER":
        return "C"
    return "Avoid"


def calculate_position_size(entry, stop, account_size=ACCOUNT_SIZE, risk_pct=RISK_PER_TRADE_PCT):
    try:
        entry = float(entry)
        stop = float(stop)
        account_size = float(account_size)
        risk_pct = float(risk_pct)
    except Exception:
        return {
            "risk_amount": 0,
            "risk_per_share": 0,
            "max_position_value": 0,
            "max_shares": 0,
            "max_lots": 0,
        }

    risk_amount = account_size * (risk_pct / 100.0)
    risk_per_share = max(entry - stop, 0)

    if risk_per_share <= 0 or entry <= 0:
        return {
            "risk_amount": round(risk_amount, 2),
            "risk_per_share": 0,
            "max_position_value": 0,
            "max_shares": 0,
            "max_lots": 0,
        }

    max_shares = int(risk_amount // risk_per_share)
    max_lots = max_shares // 100
    max_position_value = max_shares * entry

    return {
        "risk_amount": round(risk_amount, 2),
        "risk_per_share": round(risk_per_share, 2),
        "max_position_value": round(max_position_value, 2),
        "max_shares": int(max_shares),
        "max_lots": int(max_lots),
    }


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
    codes = set()
    for raw_line in text.splitlines():
        line = " ".join(raw_line.strip().split())
        m = re.match(r"^\d+\s+([A-Z]{4,5})\s+PT\b", line)
        if m:
            codes.add(m.group(1))
    return sorted(codes)


def update_syariah_universe(force_download=False):
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
# MARKET FILTER
# =========================================================
def get_market_filter_data():
    try:
        idx = yf.Ticker(MARKET_SYMBOL)
        df = idx.history(period="6mo", interval="1d", auto_adjust=False)
        if df.empty or len(df) < 60:
            return {
                "symbol": MARKET_SYMBOL,
                "available": False,
                "status": "Data tidak tersedia",
                "market_ok": True,
                "close": 0,
                "ma20": 0,
                "ma50": 0,
                "rsi14": 0,
            }

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.copy()
        df["SMA20"] = ta.sma(df["Close"], length=20)
        df["SMA50"] = ta.sma(df["Close"], length=50)
        df["RSI14"] = ta.rsi(df["Close"], length=14)
        df = df.dropna().copy()

        if df.empty:
            return {
                "symbol": MARKET_SYMBOL,
                "available": False,
                "status": "Indikator tidak cukup",
                "market_ok": True,
                "close": 0,
                "ma20": 0,
                "ma50": 0,
                "rsi14": 0,
            }

        last = df.iloc[-1]
        close = float(last["Close"])
        ma20 = float(last["SMA20"])
        ma50 = float(last["SMA50"])
        rsi14 = float(last["RSI14"])

        market_ok = close > ma20 and ma20 >= ma50 and rsi14 >= 45

        if close > ma20 and ma20 >= ma50 and rsi14 >= 55:
            status = "Uptrend / mendukung"
        elif close >= ma20 and rsi14 >= 45:
            status = "Sideways sehat / masih mendukung"
        else:
            status = "Market lemah / kurang mendukung"

        return {
            "symbol": MARKET_SYMBOL,
            "available": True,
            "status": status,
            "market_ok": market_ok if USE_MARKET_FILTER else True,
            "close": round(close, 2),
            "ma20": round(ma20, 2),
            "ma50": round(ma50, 2),
            "rsi14": round(rsi14, 2),
        }

    except Exception as e:
        log(f"Market filter error: {e}")
        return {
            "symbol": MARKET_SYMBOL,
            "available": False,
            "status": f"Error: {e}",
            "market_ok": True,
            "close": 0,
            "ma20": 0,
            "ma50": 0,
            "rsi14": 0,
        }


# =========================================================
# TEKNIKAL
# =========================================================
def get_price_structure(df):
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
    close = data["Close Price"]
    vol = data["Volume"]
    vol_sma20 = data["Volume_SMA_20"]
    rsi = data["RSI_14"]

    bullish_stack = close > ma10 > ma20 > ma50
    bearish_stack = close < ma10 < ma20 < ma50

    if bullish_stack and vol > vol_sma20 and rsi >= 60:
        return "Markup / Bullish Continuation"
    elif close > ma20 and ma20 > ma50 and rsi >= 55:
        return "Early Markup"
    elif bearish_stack and rsi < 45:
        return "Markdown"
    elif close > ma20 and vol < vol_sma20:
        return "Konsolidasi dalam uptrend"
    elif close < ma20 and vol < vol_sma20:
        return "Sideways / distribusi ringan"
    return "Transisi"


def get_support_resistance_levels(df, close_price):
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
        df["HIGH_20"] = df["High"].rolling(20).max()
        df["LOW_20"] = df["Low"].rolling(20).min()
        df["ATR_14"] = ta.atr(df["High"], df["Low"], df["Close"], length=14)
        df = df.dropna().copy()

        if df.empty or len(df) < 30:
            return None

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        close_price = round(float(latest["Close"]), 2)
        open_price = round(float(latest["Open"]), 2)
        high_price = round(float(latest["High"]), 2)
        low_price = round(float(latest["Low"]), 2)
        prev_close = round(float(prev["Close"]), 2)
        prev_open = round(float(prev["Open"]), 2)
        prev_high = round(float(prev["High"]), 2)
        prev_low = round(float(prev["Low"]), 2)

        volume = float(latest["Volume"]) if pd.notna(latest["Volume"]) else 0
        prev_volume = float(prev["Volume"]) if pd.notna(prev["Volume"]) else 0
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
        atr14 = round(float(latest["ATR_14"]), 2) if pd.notna(latest["ATR_14"]) else 0.0

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
            "Open Price": open_price,
            "High Price": high_price,
            "Low Price": low_price,
            "Prev Close": prev_close,
            "Prev Open": prev_open,
            "Prev High": prev_high,
            "Prev Low": prev_low,
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
            "Prev Volume": int(prev_volume),
            "Volume_SMA_20": int(vol_sma20),
            "MFI_14": mfi14,
            "ATR_14": atr14,
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
# TRIGGER & SCENARIO ENGINE
# =========================================================
def detect_bullish_candle_signal(data):
    close = data["Close Price"]
    open_ = data["Open Price"]
    high = data["High Price"]
    low = data["Low Price"]
    prev_close = data["Prev Close"]
    prev_open = data["Prev Open"]

    candle_range = max(high - low, 0.01)
    body = abs(close - open_)
    lower_wick = min(open_, close) - low
    hammer_like = lower_wick >= body * 1.5 and body / candle_range <= 0.45
    bullish_body = close > open_
    bullish_engulfing_like = close > prev_open and open_ <= prev_close and close > open_ and prev_close < prev_open
    recovery_close = close > prev_close

    return hammer_like or bullish_engulfing_like or (bullish_body and recovery_close)


def detect_pullback_trigger(data, support_area):
    close = data["Close Price"]
    low = data["Low Price"]
    prev_close = data["Prev Close"]
    volume = data["Volume"]
    prev_volume = data["Prev Volume"]

    near_support = low <= support_area * 1.02 or close <= support_area * 1.03
    candle_ok = detect_bullish_candle_signal(data)
    volume_ok = volume > prev_volume or volume > data["Volume_SMA_20"]
    rebound_ok = close > prev_close

    return near_support and candle_ok and volume_ok and rebound_ok


def detect_breakout_trigger(data, breakout_level):
    close = data["Close Price"]
    high = data["High Price"]
    volume = data["Volume"]
    vol_sma20 = data["Volume_SMA_20"]

    close_break = close > breakout_level
    high_break = high > breakout_level
    volume_spike = volume > vol_sma20 * 1.2

    return (close_break or high_break) and volume_spike


def build_trade_management_plan(entry, tp1):
    return [
        f"Jika harga naik {format_percent(MOVE_SL_TO_BEP_AT_PCT)}, geser SL ke BEP ({format_price(entry)}).",
        f"Jika TP1 ({format_price(tp1)}) tercapai, ambil partial profit {PARTIAL_TAKE_PROFIT_AT_TP1_PCT:.0f}%.",
        "Sisa posisi diarahkan ke TP2 dengan SL dinaikkan ke area entry / di atas BEP.",
    ]


def build_trade_scenarios(data):
    close = data["Close Price"]
    ma10 = data["MA10"]
    ma20 = data["MA20"]
    atr = max(data["ATR_14"], 0.01)
    s1 = data["support_1"]
    r1 = data["resistance_1"]
    r2 = data["resistance_2"]
    r3 = data["resistance_3"]

    # Pullback scenario
    pullback_area = round(max(ma20, s1), 2)
    pullback_entry = round(pullback_area, 2)

    tactical_pullback_sl = round(max(pullback_entry - atr * 0.5, pullback_entry * (1 - min(0.03, MAX_STOP_DECIMAL)), s1 * 0.995), 2)
    structural_pullback_sl = round(max(min(s1 * 0.99, pullback_entry * (1 - MAX_STOP_DECIMAL)), pullback_entry * (1 - MAX_STOP_DECIMAL)), 2)

    if tactical_pullback_sl >= pullback_entry:
        tactical_pullback_sl = round(pullback_entry * (1 - min(0.03, MAX_STOP_DECIMAL)), 2)
    if structural_pullback_sl >= pullback_entry:
        structural_pullback_sl = round(pullback_entry * (1 - MAX_STOP_DECIMAL), 2)

    pullback_tp1 = round(max(r1, pullback_entry * STYLE_CONFIG["tp1_mult"]), 2)
    pullback_tp2 = round(max(r2, pullback_entry * STYLE_CONFIG["tp2_mult"]), 2)
    pullback_rr_tactical = calc_rr(pullback_entry, tactical_pullback_sl, pullback_tp2)
    pullback_rr_structural = calc_rr(pullback_entry, structural_pullback_sl, pullback_tp2)
    pullback_trigger_ready = detect_pullback_trigger(data, pullback_area)

    # Breakout scenario with style-based buffer
    breakout_level = round(max(r1, close), 2)
    breakout_entry = round(max(
        breakout_level * (1 + BREAKOUT_BUFFER_PCT),
        breakout_level + BREAKOUT_BUFFER_ABS
    ), 2)

    tactical_breakout_sl = round(max(breakout_entry - atr * 0.7, breakout_entry * (1 - min(0.04, MAX_STOP_DECIMAL)), ma10, breakout_level * 0.98), 2)
    structural_breakout_sl = round(max(min(ma20, breakout_level * 0.97, breakout_entry * (1 - MAX_STOP_DECIMAL)), breakout_entry * (1 - MAX_STOP_DECIMAL)), 2)

    if tactical_breakout_sl >= breakout_entry:
        tactical_breakout_sl = round(breakout_entry * (1 - min(0.04, MAX_STOP_DECIMAL)), 2)
    if structural_breakout_sl >= breakout_entry:
        structural_breakout_sl = round(breakout_entry * (1 - MAX_STOP_DECIMAL), 2)

    breakout_tp1 = round(max(r2, breakout_entry * STYLE_CONFIG["tp1_mult"]), 2)
    breakout_tp2 = round(max(r3, breakout_entry * STYLE_CONFIG["tp2_mult"]), 2)
    breakout_rr_tactical = calc_rr(breakout_entry, tactical_breakout_sl, breakout_tp2)
    breakout_rr_structural = calc_rr(breakout_entry, structural_breakout_sl, breakout_tp2)
    breakout_trigger_ready = detect_breakout_trigger(data, breakout_level)

    pullback_pos = calculate_position_size(pullback_entry, tactical_pullback_sl)
    breakout_pos = calculate_position_size(breakout_entry, tactical_breakout_sl)

    pullback = {
        "name": "Pullback Entry",
        "area": pullback_area,
        "trigger_text": "Bullish candle + rebound + volume naik",
        "trigger_ready": pullback_trigger_ready,
        "entry": pullback_entry,
        "sl_tactical": tactical_pullback_sl,
        "sl_structural": structural_pullback_sl,
        "tp1": pullback_tp1,
        "tp2": pullback_tp2,
        "rr_tactical": round(pullback_rr_tactical, 2),
        "rr_structural": round(pullback_rr_structural, 2),
        "expiry_days": PULLBACK_EXPIRY_DAYS,
        "position": pullback_pos,
        "trade_management": build_trade_management_plan(pullback_entry, pullback_tp1),
    }

    breakout = {
        "name": "Breakout Entry",
        "area": breakout_level,
        "trigger_text": f"Close breakout + volume spike + buffer {format_percent(BREAKOUT_BUFFER_PCT*100)}",
        "trigger_ready": breakout_trigger_ready,
        "entry": breakout_entry,
        "sl_tactical": tactical_breakout_sl,
        "sl_structural": structural_breakout_sl,
        "tp1": breakout_tp1,
        "tp2": breakout_tp2,
        "rr_tactical": round(breakout_rr_tactical, 2),
        "rr_structural": round(breakout_rr_structural, 2),
        "expiry_days": 1,
        "position": breakout_pos,
        "trade_management": build_trade_management_plan(breakout_entry, breakout_tp1),
    }

    return pullback, breakout


# =========================================================
# REPORT RULE-BASED (PRO v3)
# =========================================================
def generate_python_logic_report(data, return_meta=False):
    close = data["Close Price"]
    ma10 = data["MA10"]
    ma20 = data["MA20"]
    ma50 = data["MA50"]
    rsi = data["RSI_14"]
    macd = data["MACD"]
    macd_signal = data["MACD_Signal"]
    macd_hist = data["MACD_Hist"]
    prev_macd_hist = data["Prev_MACD_Hist"]
    bb_upper = data["BB_Upper"]
    bb_lower = data["BB_Lower"]
    volume = data["Volume"]
    vol_sma20 = max(data["Volume_SMA_20"], 1)
    mfi = data["MFI_14"]

    s1 = data["support_1"]
    s2 = data["support_2"]
    s3 = data["support_3"]
    r1 = data["resistance_1"]
    r2 = data["resistance_2"]
    r3 = data["resistance_3"]

    breakout_valid = data["Breakout_Valid"]
    structure_flag = data["Structure_Flag"]
    phase_text = data["Market_Phase"]

    market_filter = get_market_filter_data()

    bullish_ma_alignment = close > ma20 > ma50
    strong_bullish_ma = close > ma10 > ma20 > ma50
    bullish_macd = macd > macd_signal
    bullish_volume = volume > vol_sma20
    bullish_rsi = rsi >= 60

    if breakout_valid and bullish_ma_alignment and bullish_macd and bullish_volume:
        trend_condition = "Bullish continuation / breakout confirmation"
        trend_bias = "Bullish kuat"
    elif strong_bullish_ma and bullish_macd and bullish_rsi:
        trend_condition = "Uptrend kuat"
        trend_bias = "Bullish kuat"
    elif bullish_ma_alignment and structure_flag in ["bullish", "reversal"]:
        trend_condition = "Early uptrend / transisi bullish"
        trend_bias = "Bullish moderat"
    elif close < ma20 < ma50 and structure_flag == "bearish":
        trend_condition = "Downtrend"
        trend_bias = "Bearish kuat"
    else:
        trend_condition = "Sideways / transisi"
        trend_bias = "Netral"

    if close > bb_upper:
        condition_text = "Overextended / breakout kuat"
    elif rsi >= 75:
        condition_text = "Bullish panas / rawan pullback sehat"
    elif bullish_ma_alignment:
        condition_text = "Bullish sehat"
    elif close < bb_lower:
        condition_text = "Tekanan jual tinggi"
    else:
        condition_text = "Netral / menunggu konfirmasi"

    if macd > macd_signal and macd_hist > prev_macd_hist:
        macd_signal_text = "Golden cross + histogram menguat"
    elif macd > macd_signal:
        macd_signal_text = "Golden cross"
    elif macd < macd_signal and macd_hist < prev_macd_hist:
        macd_signal_text = "Dead cross + histogram melemah"
    else:
        macd_signal_text = "MACD campuran"

    if volume > vol_sma20 * 2:
        volume_signal = "Volume melonjak sangat besar"
    elif volume > vol_sma20 * 1.5:
        volume_signal = "Volume tinggi"
    elif volume > vol_sma20:
        volume_signal = "Volume di atas rata-rata"
    else:
        volume_signal = "Volume normal / belum kuat"

    if mfi >= 85:
        mfi_signal = f"MFI ±{round(mfi)} → dana masuk sangat kuat, rawan profit taking"
    elif mfi >= 65:
        mfi_signal = f"MFI ±{round(mfi)} → dana masuk kuat"
    elif mfi <= 20:
        mfi_signal = f"MFI ±{round(mfi)} → dana lemah, potensi rebound"
    else:
        mfi_signal = f"MFI ±{round(mfi)} → dana moderat"

    if rsi >= 80:
        rsi_signal = f"RSI ±{round(rsi)} → sangat panas"
    elif rsi >= 70:
        rsi_signal = f"RSI ±{round(rsi)} → bullish kuat"
    elif rsi >= 60:
        rsi_signal = f"RSI ±{round(rsi)} → bullish sehat"
    elif rsi <= 30:
        rsi_signal = f"RSI ±{round(rsi)} → oversold"
    else:
        rsi_signal = f"RSI ±{round(rsi)} → netral"

    pullback, breakout = build_trade_scenarios(data)

    rr_best = max(pullback["rr_tactical"], breakout["rr_tactical"])
    rr_status = rr_quality_label(rr_best)

    pullback_confirmed = pullback["trigger_ready"] and pullback["rr_tactical"] >= MIN_ACCEPTABLE_RR
    breakout_confirmed = breakout["trigger_ready"] and breakout["rr_tactical"] >= MIN_ACCEPTABLE_RR

    if not market_filter["market_ok"] and STYLE_CONFIG["entry_ready_requires_market"]:
        if trend_bias.startswith("Bullish"):
            action_status = "WAIT FOR TRIGGER"
        else:
            action_status = "SKIP"
    else:
        if breakout_confirmed or pullback_confirmed:
            action_status = "ENTRY READY"
        elif trend_bias.startswith("Bullish"):
            action_status = "WAIT FOR TRIGGER"
        else:
            action_status = "SKIP"

    setup_grade = get_setup_grade(
        action_status,
        rr_best,
        breakout_confirmed,
        pullback_confirmed,
        market_filter["market_ok"]
    )

    preferred_style_scenario = STYLE_CONFIG["preferred_scenario"]
    if preferred_style_scenario == "breakout":
        preferred = breakout if breakout["rr_tactical"] >= MIN_ACCEPTABLE_RR else pullback
        preferred_label = "Breakout" if preferred is breakout else "Pullback"
    else:
        preferred = pullback if pullback["rr_tactical"] >= MIN_ACCEPTABLE_RR else breakout
        preferred_label = "Pullback" if preferred is pullback else "Breakout"

    if action_status == "ENTRY READY":
        final_conclusion = f"Setup siap dieksekusi. Prioritas mode {STYLE_CONFIG['label']} mengarah ke skenario {preferred_label} dengan RR {preferred['rr_tactical']}."
    elif action_status == "WAIT FOR TRIGGER":
        if not market_filter["market_ok"] and STYLE_CONFIG["entry_ready_requires_market"]:
            final_conclusion = f"Setup saham menarik, tetapi market filter {MARKET_SYMBOL} belum mendukung. Tunggu market membaik."
        else:
            final_conclusion = f"Mode {STYLE_CONFIG['label']} menunggu trigger valid agar entry lebih presisi dan RR membaik."
    else:
        final_conclusion = "Setup tidak layak untuk sekarang. Fokus proteksi modal."

    best_position = pullback["position"] if preferred is pullback else breakout["position"]
    best_management = pullback["trade_management"] if preferred is pullback else breakout["trade_management"]

    report = f"""📊 ANALISIS TEKNIKAL — ${denormalize_ticker(data["Ticker"])} (Daily)
Mode: {STYLE_CONFIG["label"]}

1. Decision Engine
• Trend      : {trend_condition}
• Kondisi    : {condition_text}
• Market     : {market_filter["status"]}
• RR Status  : {rr_status}
• Action     : {action_status}
• Grade      : {setup_grade}

2. Konteks Teknikal
• Fase       : {phase_text}
• Struktur   : {data["Price_Structure"]}
• RSI        : {rsi_signal}
• MACD       : {macd_signal_text}
• Volume     : {volume_signal} ({format_big_number(volume)} vs avg20 {format_big_number(vol_sma20)})
• MFI        : {mfi_signal}

3. Support / Resistance
• Support    : {format_price(s1)} | {format_price(s2)} | {format_price(s3)}
• Resistance : {format_price(r1)} | {format_price(r2)} | {format_price(r3)}

4. Skenario Pullback Entry
• Area         : {format_price(pullback["area"])}
• Trigger      : {pullback["trigger_text"]}
• Status       : {"VALID" if pullback["trigger_ready"] else "WAIT"}
• Entry        : {format_price(pullback["entry"])}
• Tactical SL  : {format_price(pullback["sl_tactical"])}
• Structural SL: {format_price(pullback["sl_structural"])}
• TP           : {format_price(pullback["tp1"])} | {format_price(pullback["tp2"])}
• RR Tactical  : {pullback["rr_tactical"]}
• RR Structural: {pullback["rr_structural"]}
• Expiry       : {pullback["expiry_days"]} hari bursa

5. Skenario Breakout Entry
• Area         : > {format_price(breakout["area"])}
• Trigger      : {breakout["trigger_text"]}
• Status       : {"VALID" if breakout["trigger_ready"] else "WAIT"}
• Entry        : {format_price(breakout["entry"])}
• Tactical SL  : {format_price(breakout["sl_tactical"])}
• Structural SL: {format_price(breakout["sl_structural"])}
• TP           : {format_price(breakout["tp1"])} | {format_price(breakout["tp2"])}
• RR Tactical  : {breakout["rr_tactical"]}
• RR Structural: {breakout["rr_structural"]}

6. Position Sizing (Skenario Prioritas)
• Modal            : {format_big_number(ACCOUNT_SIZE)}
• Risk per trade   : {RISK_PER_TRADE_PCT:.2f}%
• Skenario pilih   : {preferred_label}
• Risk nominal     : {format_big_number(best_position["risk_amount"])}
• Maks posisi      : {format_big_number(best_position["max_position_value"])}
• Estimasi lot     : {best_position["max_lots"]} lot

7. Trade Management
• {best_management[0]}
• {best_management[1]}
• {best_management[2]}

8. Catatan Mode
• {STYLE_CONFIG["description"]}

9. Ringkasan
• Harga saat ini : {format_price(close)}
• Kesimpulan     : {final_conclusion}
"""

    meta = {
        "action_status": action_status,
        "setup_grade": setup_grade,
        "rr_best": rr_best,
        "pullback_confirmed": pullback_confirmed,
        "breakout_confirmed": breakout_confirmed,
        "market_ok": market_filter["market_ok"],
        "market_filter": market_filter,
        "pullback": pullback,
        "breakout": breakout,
        "style": TRADING_STYLE,
    }

    if return_meta:
        return report.strip(), meta
    return report.strip()



# =========================================================
# FEED EXPORT
# =========================================================
def build_screener_feed_json(screened_df: pd.DataFrame, market_filter=None):
    market_filter = market_filter or get_market_filter_data()
    items = []

    if screened_df is not None and not screened_df.empty:
        for _, row in screened_df.iterrows():
            ticker = str(row.get("Ticker", "")).strip().upper()
            ticker_yf = str(row.get("Ticker_YF", f"{ticker}.JK"))

            tech_data = get_technical_data(ticker_yf)
            if not tech_data:
                continue

            _, meta = generate_python_logic_report(tech_data, return_meta=True)

            preferred_key = "breakout" if str(meta.get("preferred_label", "")).lower() == "breakout" else "pullback"
            preferred = meta.get(preferred_key, {}) or {}

            signal, strategy, _ = build_signal_and_strategy(meta)

            notes_parts = []
            if bool(row.get("Volume_OK", True)):
                notes_parts.append("Volume naik")
            if preferred_key == "breakout":
                notes_parts.append("breakout resistance minor")
            else:
                notes_parts.append("rebound area pullback")
            if bool(row.get("Market_OK", True)):
                notes_parts.append("market mendukung")
            notes = ", ".join(notes_parts).capitalize() if notes_parts else "Setup terdeteksi"

            items.append({
                "ticker": ticker,
                "name": get_company_name(ticker_yf, fallback_ticker=ticker),
                "price": round(float(row.get("Close", 0) or 0), 2),
                "change_pct": round(float(row.get("Ret_1D_Pct", 0) or 0), 2),
                "score": round(float(row.get("Score", 0) or 0)),
                "signal": signal,
                "strategy": strategy,
                "entry": round(float(preferred.get("entry", row.get("Close", 0) or 0)), 2),
                "take_profit": round(float(preferred.get("tp1", 0) or 0), 2),
                "stop_loss": round(float(preferred.get("sl_tactical", 0) or 0), 2),
                "notes": notes
            })

    items = sorted(items, key=lambda x: x.get("score", 0), reverse=True)

    return {
        "meta": {
            "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": "IDX Technical Analyst Hybrid Engine PRO v3 Feed"
        },
        "summary": {
            "count": len(items),
            "top_tickers": [x["ticker"] for x in items[:10]]
        },
        "items": items
    }


def export_screener_json(screened_df: pd.DataFrame, output_path: str = SCREENER_JSON_OUTPUT):
    payload = build_screener_feed_json(screened_df, market_filter=get_market_filter_data())
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    log(f"Screener JSON exported: {output_file}")

# =========================================================
# AI INSIGHT OPSIONAL
# =========================================================
def generate_ai_insight(data, python_report):
    if not ENABLE_AI_INSIGHT:
        return ""

    prompt = f"""
Anda adalah analis teknikal saham Indonesia.
Berdasarkan data berikut, buat insight singkat maksimal 5 poin.
Fokus: trend, momentum, trigger entry, risiko, dan manajemen posisi.
Sesuaikan dengan mode trading: {STYLE_CONFIG["label"]}.
Jangan mengulang isi report Python.

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
    df["VOL_SMA20"] = df["Volume"].rolling(20).mean()
    df["RET_1D_PCT"] = df["Close"].pct_change() * 100
    df["VALUE_TRADED"] = df["Close"] * df["Volume"]
    df["HIGH_20"] = df["High"].rolling(20).max()
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


def _analyze_screener_row(ticker: str, df: pd.DataFrame, market_ok=True):
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
    sma20_slope_5 = _safe_float(last["SMA20_SLOPE_5"])

    if close <= 0 or vol_sma20 <= 0:
        return None

    volume_ratio = volume / vol_sma20 if vol_sma20 > 0 else 0.0
    distance_to_high_20_pct = ((close / high_20) - 1) * 100 if high_20 > 0 else 0.0

    trend_ok = (
        close > sma20 and
        sma20 > sma50 and
        sma20_slope_5 > 0 and
        rsi14 >= SCREENER_MIN_RSI and
        macd > macd_signal
    )

    price_ok = close < SCREENER_MAX_PRICE
    volume_ok = volume_ratio >= SCREENER_MIN_VOLUME_RATIO
    return_ok = ret_1d > 0
    liquidity_ok = value_traded >= SCREENER_MIN_VALUE_TRADED
    market_filter_ok = market_ok if USE_MARKET_FILTER else True

    # Market filter disimpan sebagai konteks, bukan pemblokir total feed JSON/web app.
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
        "Eligible": bool(eligible),
        "Market_OK": bool(market_filter_ok),
        "Near_High_20_Pct": round(distance_to_high_20_pct, 2),
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

    market_filter = get_market_filter_data()
    market_ok = market_filter["market_ok"]

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
                row = _analyze_screener_row(ticker, prepared, market_ok=market_ok)
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
    market_filter = get_market_filter_data()

    if df is None or df.empty:
        return (
            f"📌 Screener Saham Syariah Trending ({STYLE_CONFIG['label']})\n\n"
            f"Market filter: {market_filter['status']}\n\n"
            "Tidak ada saham yang lolos filter hari ini.\n"
            "Filter aktif:\n"
            "• Harga < 100\n"
            "• Volume > 1.5x rata-rata 20 hari\n"
            "• Return harian positif\n"
            "• Close > SMA20 > SMA50\n"
            "• RSI dan MACD bullish\n"
            "• Market filter IHSG mendukung"
        )

    lines = [
        f"📌 Screener Saham Syariah Trending ({STYLE_CONFIG['label']})",
        "",
        f"Market filter: {market_filter['status']}",
        "",
        "Kriteria:",
        "• Harga < 100",
        "• Volume > 1.5x rata-rata 20 hari",
        "• Return harian positif",
        "• Close > SMA20 > SMA50",
        "• RSI dan MACD bullish",
        "• Market filter IHSG mendukung",
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
    python_report, meta = generate_python_logic_report(data, return_meta=True)

    if meta["action_status"] == "SKIP":
        return python_report

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
        f"🚀 Mode: WATCHLIST ({STYLE_CONFIG['label']})\n"
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
    log("Masuk ke mode SCREENER SYARIAH")

    if SCREENER_ENABLE_AUTO_UPDATE_UNIVERSE:
        try:
            update_syariah_universe(force_download=False)
            log("Universe syariah berhasil diupdate")
        except Exception as e:
            log(f"Auto update universe gagal, lanjut pakai file existing: {e}")

    screened_df = screen_syariah_stocks(limit=SCREENER_LIMIT)
    export_screener_json(screened_df)
    log(f"Jumlah kandidat screener: {0 if screened_df is None else len(screened_df)}")

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
    if SCREENER_ENABLE_AUTO_UPDATE_UNIVERSE:
        try:
            update_syariah_universe(force_download=False)
        except Exception as e:
            log(f"Auto update universe gagal, lanjut pakai file existing: {e}")

    screened_df = screen_syariah_stocks(limit=SCREENER_LIMIT)
    export_screener_json(screened_df)
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
            f"📋 Tambahan analisa watchlist manual ({STYLE_CONFIG['label']})\n"
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
    log(f"TRADING_STYLE = {TRADING_STYLE}")
    log(f"STYLE_LABEL = {STYLE_CONFIG['label']}")
    log(f"WATCHLIST_FILE = {WATCHLIST_FILE}")
    log(f"SYARIAH_UNIVERSE_FILE = {SYARIAH_UNIVERSE_FILE}")
    log(f"SCREENER_ENABLE_AUTO_UPDATE_UNIVERSE = {SCREENER_ENABLE_AUTO_UPDATE_UNIVERSE}")
    log(f"SCREENER_MAX_PRICE = {SCREENER_MAX_PRICE}")
    log(f"SCREENER_JSON_OUTPUT = {SCREENER_JSON_OUTPUT}")
    log(f"ACCOUNT_SIZE = {ACCOUNT_SIZE}")
    log(f"RISK_PER_TRADE_PCT = {RISK_PER_TRADE_PCT}")
    log(f"MAX_STOP_PCT = {MAX_STOP_PCT}")
    log(f"BREAKOUT_BUFFER_PCT = {BREAKOUT_BUFFER_PCT}")
    log(f"BREAKOUT_BUFFER_ABS = {BREAKOUT_BUFFER_ABS}")
    log(f"PULLBACK_EXPIRY_DAYS = {PULLBACK_EXPIRY_DAYS}")
    log(f"USE_MARKET_FILTER = {USE_MARKET_FILTER}")
    log(f"MARKET_SYMBOL = {MARKET_SYMBOL}")

    try:
        if RUN_MODE == "screener_syariah":
            run_screener_syariah_mode()
        elif RUN_MODE == "hybrid":
            run_hybrid_mode()
        elif RUN_MODE == "watchlist":
            run_watchlist_mode()
        else:
            raise ValueError(f"RUN_MODE tidak valid: {RUN_MODE}")
    except Exception as e:
        log(f"Fatal error: {e}")
        send_to_telegram(f"❌ Bot saham mengalami error fatal:\n{e}")


if __name__ == "__main__":
    main()
