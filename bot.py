import os
import requests
import time
import pandas as pd
from datetime import datetime
from vnstock import Vnstock

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

WATCHLIST = [
    "VCB","ACB","CTG","FPT","MWG","SCS","GMD","GAS","BSR","PVT",
    "NT2","DPG","HHV","PC1","KSB","IDC","SZC","VNM","QNS","VHC",
    "HSG","SSI","HCM","FTS","DHG","DBD","BVH","PVI","TNG","DPR",
    "VOS","BMP"
]

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    try:
        response = requests.post(url, data=payload, timeout=15)
        print("Da gui:", response.status_code)
    except Exception as e:
        print("Loi gui tin:", e)

def lay_gia_realtime(symbol):
    try:
        stock = Vnstock().stock(symbol=symbol, source='VCI')
        board = stock.trading.price_board(symbols_list=[symbol])
        gia = board[('match', 'match_price')].iloc[0]
        if gia and float(gia) > 0:
            return float(gia)
        return None
    except Exception:
        return None

def lay_khoi_ngoai(symbol):
    try:
        stock = Vnstock().stock(symbol=symbol, source='VCI')
        df = stock.trading.foreign_trade(symbol=symbol)
        if df is None or len(df) == 0:
            return None
        row = df.iloc[-1]
        return row.to_dict()
    except Exception as e:
        print(f"Loi lay khoi ngoai {symbol}: {e}")
        return None

def tinh_rsi(closes, window=14):
    delta = closes.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def tinh_macd(closes):
    ema12 = closes.ewm(span=12, adjust=False).mean()
    ema26 = closes.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    return macd_line, signal_line

def tinh_ho_tro_khang_cu(df, window=20):
    gan_day = df.tail(window)
    return gan_day['low'].astype(float).min() * 1000, gan_day['high'].astype(float).max() * 1000

def quyet_dinh(rsi, macd_tich_cuc, tren_ma, gan_ho_tro, gan_khang_cu):
    if rsi < 30 and macd_tich_cuc and gan_ho_tro:
        return "MUA", "RSI qua ban + MACD tich cuc + gan ho tro"
    if rsi > 70 and not macd_tich_cuc and gan_khang_cu:
        return "BAN", "RSI qua mua + MACD tieu cuc + gan khang cu"
    if tren_ma and macd_tich_cuc and 40 <= rsi <= 65:
        return "GIU/MUA THEM", "Tren MA20/MA50, MACD tot, RSI an toan"
    if not tren_ma and not macd_tich_cuc:
        return "TRANH", "Duoi MA20/MA50, MACD xau"
    if gan_ho_tro and macd_tich_cuc:
        return "CAN NHAC MUA", "Gan ho tro, MACD dang tot"
    if gan_khang_cu and not macd_tich_cuc:
        return "CAN NHAC BAN", "Gan khang cu, MACD yeu"
    return "QUAN SAT", "Tin hieu chua ro"

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
            return f"{symbol}: Khong du du lieu"

        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(float)
        closes = df['close']
        volumes = df['volume']

        gia_dong_cua_gan_nhat = closes.iloc[-1] * 1000
        gia_phien_truoc = closes.iloc[-2] * 1000

        gia_rt = lay_gia_realtime(symbol)
        la_rt = gia_rt is not None
        gia_hien_tai = gia_rt if la_rt else gia_dong_cua_gan_nhat
        thay_doi = ((gia_hien_tai - gia_phien_truoc) / gia_phien_truoc) * 100

        kl_hom_nay = volumes.iloc[-1]
        kl_tb20 = volumes.tail(20).mean()
        kl_ty_le = (kl_hom_nay / kl_tb20) * 100 if kl_tb20 > 0 else 0

        rsi = tinh_rsi(closes).iloc[-1]
        macd_line, signal_line = tinh_macd(closes)
        macd_tc = macd_line.iloc[-1] > signal_line.iloc[-1]

        ma20 = closes.rolling(window=20).mean().iloc[-1]
        ma50 = closes.rolling(window=50).mean().iloc[-1]
        tren_ma = gia_hien_tai > ma20 * 1000 and ma20 > ma50

        ho_tro, khang_cu = tinh_ho_tro_khang_cu(df)
        gan_ht = abs(gia_hien_tai - ho_tro) / ho_tro * 100 <= 3
        gan_kc = abs(gia_hien_tai - khang_cu) / khang_cu * 100 <= 3

        hanh_dong, ly_do = quyet_dinh(rsi, macd_tc, tren_ma, gan_ht, gan_kc)
        dau = "UP" if thay_doi >= 0 else "DOWN"
        nhan_gia = "(realtime)" if la_rt else "(dong cua)"
        stoploss = ho_tro * 0.97 if hanh_dong in ["MUA","CAN NHAC MUA","GIU/MUA THEM"] else khang_cu * 1.03

        ket_qua = f"=== {symbol} {nhan_gia}: {gia_hien_tai:,.0f}d ({thay_doi:+.2f}%) ===\n"
        ket_qua += f">>> {hanh_dong} <<< ({ly_do})\n"
        ket_qua += f"KL: {kl_hom_nay:,.0f} ({kl_ty_le:.0f}% TB20)\n"

        kn = lay_khoi_ngoai(symbol)
        if kn:
            ket_qua += f"KhoiNgoai: {kn}\n"

        ket_qua += f"RSI:{rsi:.0f} MACD:{'tot' if macd_tc else 'xau'} HT:{ho_tro:,.0f}d KC:{khang_cu:,.0f}d SL:{stoploss:,.0f}d"
        return ket_qua

    except Exception as e:
        return f"{symbol}: Loi ({str(e)[:50]})"

def main():
    now = datetime.now().strftime("%H:%M %d/%m/%Y")
    message = f"BAO CAO QUYET DINH - {now}\n\n"
    message += get_vnindex() + "\n\n"

    for symbol in WATCHLIST:
        message += phan_tich_ma(symbol) + "\n\n"
        time.sleep(1.2)

    send_message(message)

if __name__ == "__main__":
    main()
