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

def tinh_ho_tro_khang_cu(df, window=20):
    gan_day = df.tail(window)
    khang_cu = gan_day['high'].astype(float).max()
    ho_tro = gan_day['low'].astype(float).min()
    return ho_tro, khang_cu

def lay_mua_ban_chu_dong(symbol):
    """Thu lay du lieu khop lenh trong ngay de tinh mua/ban chu dong"""
    try:
        stock = Vnstock().stock(symbol=symbol, source='VCI')
        intraday = stock.quote.intraday(symbol=symbol, page_size=5000)
        if intraday is None or len(intraday) == 0:
            return None

        # Cot thuong co: time, price, volume, match_type (Buy/Sell) hoac tuong tu
        cols = intraday.columns.tolist()

        # Thu tim cot phan loai giao dich
        mua_kl = 0
        ban_kl = 0

        if 'match_type' in cols:
            mua_kl = intraday[intraday['match_type'] == 'Buy']['volume'].sum()
            ban_kl = intraday[intraday['match_type'] == 'Sell']['volume'].sum()
        elif 'matchType' in cols:
            mua_kl = intraday[intraday['matchType'] == 'Buy']['volume'].sum()
            ban_kl = intraday[intraday['matchType'] == 'Sell']['volume'].sum()
        else:
            return None

        return mua_kl, ban_kl
    except Exception as e:
        print(f"Khong lay duoc mua/ban chu dong cho {symbol}: {e}")
        return None

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
            return f"{symbol}: Khong du du lieu de phan tich", None

        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(float)
        closes = df['close']
        volumes = df['volume']

        gia_hom_nay = closes.iloc[-1]
        gia_hom_truoc = closes.iloc[-2]
        thay_doi = ((gia_hom_nay - gia_hom_truoc) / gia_hom_truoc) * 100

        kl_hom_nay = volumes.iloc[-1]
        kl_tb20 = volumes.tail(20).mean()
        kl_ty_le = (kl_hom_nay / kl_tb20) * 100 if kl_tb20 > 0 else 0

        rsi = tinh_rsi(closes).iloc[-1]
        macd_line, signal_line = tinh_macd(closes)
        macd_val = macd_line.iloc[-1]
        signal_val = signal_line.iloc[-1]

        ma20 = closes.rolling(window=20).mean().iloc[-1]
        ma50 = closes.rolling(window=50).mean().iloc[-1]

        ho_tro, khang_cu = tinh_ho_tro_khang_cu(df, window=20)

        dau = "UP" if thay_doi >= 0 else "DOWN"

        ghi_chu = []
        canh_bao_gia = None

        if rsi > 70:
            ghi_chu.append("RSI qua mua")
        elif rsi < 30:
            ghi_chu.append("RSI qua ban")

        if macd_val > signal_val:
            ghi_chu.append("MACD tich cuc")
        else:
            ghi_chu.append("MACD tieu cuc")

        if gia_hom_nay > ma20 and ma20 > ma50:
            ghi_chu.append("Tren MA20/MA50 - xu huong tang")
        elif gia_hom_nay < ma20 and ma20 < ma50:
            ghi_chu.append("Duoi MA20/MA50 - xu huong giam")

        if kl_ty_le >= 200:
            ghi_chu.append(f"Khoi luong dot bien ({kl_ty_le:.0f}% TB20)")

        khoang_cach_khang_cu = abs(gia_hom_nay - khang_cu) / khang_cu * 100
        khoang_cach_ho_tro = abs(gia_hom_nay - ho_tro) / ho_tro * 100

        if khoang_cach_khang_cu <= 2:
            canh_bao_gia = f"CANH BAO: {symbol} dang gan vung KHANG CU {khang_cu:,.0f}d"
        elif khoang_cach_ho_tro <= 2:
            canh_bao_gia = f"CANH BAO: {symbol} dang gan vung HO TRO {ho_tro:,.0f}d"

        ket_qua = f"{dau} {symbol}: {gia_hom_nay:,.0f}d ({thay_doi:+.2f}%)\n"
        ket_qua += f"   KL: {kl_hom_nay:,.0f} ({kl_ty_le:.0f}% TB20)\n"

        # Thu lay mua/ban chu dong
        mua_ban = lay_mua_ban_chu_dong(symbol)
        if mua_ban:
            mua_kl, ban_kl = mua_ban
            tong = mua_kl + ban_kl
            if tong > 0:
                pct_mua = (mua_kl / tong) * 100
                ket_qua += f"   Mua CD: {mua_kl:,.0f} ({pct_mua:.0f}%) | Ban CD: {ban_kl:,.0f} ({100-pct_mua:.0f}%)\n"

        ket_qua += f"   RSI: {rsi:.0f} | MA20: {ma20:,.0f} | MA50: {ma50:,.0f}\n"
        ket_qua += f"   Ho tro: {ho_tro:,.0f}d | Khang cu: {khang_cu:,.0f}d\n"
        ket_qua += f"   {', '.join(ghi_chu)}"

        return ket_qua, canh_bao_gia

    except Exception as e:
        return f"{symbol}: Loi phan tich ({str(e)[:40]})", None

def main():
    now = datetime.now().strftime("%H:%M %d/%m/%Y")

    message = f"BAO CAO DANH MUC - {now}\n\n"
    message += get_vnindex() + "\n\n"

    danh_sach_canh_bao = []

    for symbol in WATCHLIST:
        ket_qua, canh_bao = phan_tich_ma(symbol)
        message += ket_qua + "\n\n"
        if canh_bao:
            danh_sach_canh_bao.append(canh_bao)

    if danh_sach_canh_bao:
        message += "=== CANH BAO QUAN TRONG ===\n"
        message += "\n".join(danh_sach_canh_bao)

    send_message(message)

if __name__ == "__main__":
    main()
