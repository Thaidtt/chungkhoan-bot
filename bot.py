import os
import requests
import pandas as pd
from datetime import datetime
from vnstock import Vnstock

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

WATCHLIST = ["FPT", "ACV", "MBB", "HDB", "GMD", "DPG", "REE", "PVT"]

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    try:
        response = requests.post(url, data=payload, timeout=15)
        print("Da gui:", response.status_code)
    except Exception as e:
        print("Loi gui tin:", e)

def tinh_rsi(closes, window=14):
    delta = closes.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def tinh_macd(closes):
    ema12 = closes.ewm(span=12, adjust=False).mean()
    ema26 = closes.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    return macd_line, signal_line

def get_vnindex():
    try:
        stock = Vnstock().stock(symbol='VNINDEX', source='VCI')
        df = stock.quote.history(start='2026-01-01', end=datetime.now().strftime('%Y-%m-%d'), interval='1D')
        if df is None or len(df) < 2:
            return "VN-Index: Khong co du lieu"
        gia_hom_nay = df.iloc[-1]['close']
        gia_hom_truoc = df.iloc[-2]['close']
        thay_doi = ((gia_hom_nay - gia_hom_truoc) / gia_hom_truoc) * 100
        dau = "UP" if thay_doi >= 0 else "DOWN"
        return f"{dau} VN-Index: {gia_hom_nay:,.2f} ({thay_doi:+.2f}%)"
    except Exception as e:
        return f"VN-Index: Loi ({str(e)[:30]})"

def phan_tich_ma(symbol):
    try:
        stock = Vnstock().stock(symbol=symbol, source='VCI')
        df = stock.quote.history(start='2025-09-01', end=datetime.now().strftime('%Y-%m-%d'), interval='1D')

        if df is None or len(df) < 30:
            return f"{symbol}: Khong du du lieu de phan tich"

        df['close'] = df['close'].astype(float)
        closes = df['close']

        gia_hom_nay = closes.iloc[-1]
        gia_hom_truoc = closes.iloc[-2]
        thay_doi = ((gia_hom_nay - gia_hom_truoc) / gia_hom_truoc) * 100

        rsi = tinh_rsi(closes).iloc[-1]
        macd_line, signal_line = tinh_macd(closes)
        macd_val = macd_line.iloc[-1]
        signal_val = signal_line.iloc[-1]

        ma20 = closes.rolling(window=20).mean().iloc[-1]
        ma50 = closes.rolling(window=50).mean().iloc[-1]

        dau = "UP" if thay_doi >= 0 else "DOWN"

        ghi_chu = []
        if rsi > 70:
            ghi_chu.append("RSI qua mua")
        elif rsi < 30:
            ghi_chu.append("RSI qua ban")

        if macd_val > signal_val:
            ghi_chu.append("MACD tich cuc")
        else:
            ghi_chu.append("MACD tieu cuc")

        if gia_hom_nay > ma20 > ma50:
            ghi_chu.append("Tren MA20/MA50 - xu huong tang")
        elif gia_hom_nay < ma20 < ma50:
            ghi_chu.append("Duoi MA20/MA50 - xu huong giam")

        ket_qua = f"{dau} {symbol}: {gia_hom_nay:,.0f}d ({thay_doi:+.2f}%)\n"
        ket_qua += f"   RSI: {rsi:.0f} | MA20: {ma20:,.0f} | MA50: {ma50:,.0f}\n"
        ket_qua += f"   {', '.join(ghi_chu)}"

        return ket_qua

    except Exception as e:
        return f"{symbol}: Loi phan tich ({str(e)[:40]})"

def main():
    now = datetime.now().strftime("%H:%M %d/%m/%Y")

    message = f"BAO CAO DANH MUC - {now}\n\n"
    message += get_vnindex() + "\n\n"

    for symbol in WATCHLIST:
        message += phan_tich_ma(symbol) + "\n\n"

    send_message(message)

if __name__ == "__main__":
    main()
