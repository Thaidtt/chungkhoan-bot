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
    #"NT2","DPG","HHV","PC1","KSB","IDC","SZC","VNM","QNS","VHC",
    #"HSG","SSI","HCM","FTS","DHG","DBD","BVH","PVI","TNG","DPR",
    "VOS","BMP"
]

NGANH = {
    "VCB":"Ngan hang","ACB":"Ngan hang","CTG":"Ngan hang",
    "FPT":"Cong nghe","MWG":"Ban le",
    "GMD":"Cang-Logistics","SCS":"Cang-Logistics",
    "GAS":"Nang luong","PVT":"Nang luong","NT2":"Nang luong","BSR":"Nang luong",
    "DPG":"Xay dung","HHV":"Xay dung","PC1":"Xay dung","KSB":"Xay dung",
    "IDC":"BDS KCN","SZC":"BDS KCN",
    "VNM":"Tieu dung","QNS":"Tieu dung","VHC":"Tieu dung",
    "HSG":"Vat lieu",
    "SSI":"Chung khoan","HCM":"Chung khoan","FTS":"Chung khoan",
    "DHG":"Duoc pham","DBD":"Duoc pham",
    "BVH":"Bao hiem","PVI":"Bao hiem",
    "TNG":"Det may","DPR":"Cao su","VOS":"Van tai bien","BMP":"Vat lieu"
}

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

def lay_mua_ban_chu_dong(symbol):
    try:
        stock = Vnstock().stock(symbol=symbol, source='VCI')
        intraday = stock.quote.intraday(symbol=symbol, page_size=5000)
        if intraday is None or len(intraday) == 0:
            return None
        cols = intraday.columns.tolist()
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
        print(f"Khong lay duoc mua/ban chu dong {symbol}: {e}")
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
        return "MUA", "RSI qua ban + MACD tot + gan ho tro"
    if rsi > 70 and not macd_tich_cuc and gan_khang_cu:
        return "BAN", "RSI qua mua + MACD xau + gan khang cu"
    if tren_ma and macd_tich_cuc and 40 <= rsi <= 65:
        return "GIU/MUA THEM", "Tren MA20/MA50, MACD tot, RSI an toan"
    if not tren_ma and not macd_tich_cuc:
        return "TRANH", "Duoi MA20/MA50, MACD xau"
    if gan_ho_tro and macd_tich_cuc:
        return "CAN NHAC MUA", "Gan ho tro, MACD dang tot"
    if gan_khang_cu and not macd_tich_cuc:
        return "CAN NHAC BAN", "Gan khang cu, MACD yeu"
    return "QUAN SAT", "Tin hieu chua ro"

def get_tong_quan_thi_truong():
    """Lay VN-Index, thanh khoan, va tinh ngan dan dat tu watchlist"""
    try:
        stock = Vnstock().stock(symbol='VNINDEX', source='VCI')
        df = stock.quote.history(start='2026-01-01', end=datetime.now().strftime('%Y-%m-%d'), interval='1D')
        if df is None or len(df) < 2:
            return "VN-Index: Khong co du lieu", []

        gia_hom_nay = df.iloc[-1]['close']
        gia_hom_truoc = df.iloc[-2]['close']
        thay_doi = ((gia_hom_nay - gia_hom_truoc) / gia_hom_truoc) * 100
        dau = "UP" if thay_doi >= 0 else "DOWN"

        thanh_khoan = df.iloc[-1]['volume']
        thanh_khoan_tb20 = df['volume'].tail(20).mean()
        tk_ty_le = (thanh_khoan / thanh_khoan_tb20) * 100 if thanh_khoan_tb20 > 0 else 0

        ket_qua = f"{dau} VN-Index: {gia_hom_nay:,.2f} ({thay_doi:+.2f}%)\n"
        ket_qua += f"Thanh khoan: {thanh_khoan:,.0f} ({tk_ty_le:.0f}% TB20)"

        return ket_qua, None
    except Exception as e:
        return f"VN-Index: Loi ({str(e)[:30]})", None

def tinh_nganh_dan_dat(ket_qua_ca_phieu):
    """Tinh % thay doi trung binh theo nganh tu danh sach da phan tich"""
    nganh_data = {}
    for symbol, thay_doi in ket_qua_ca_phieu.items():
        nganh = NGANH.get(symbol, "Khac")
        if nganh not in nganh_data:
            nganh_data[nganh] = []
        nganh_data[nganh].append(thay_doi)

    nganh_avg = {n: sum(v)/len(v) for n, v in nganh_data.items()}
    nganh_sorted = sorted(nganh_avg.items(), key=lambda x: x[1], reverse=True)

    text = "Nganh dan dat (theo danh muc theo doi):\n"
    for nganh, avg in nganh_sorted[:3]:
        text += f"  UP {nganh}: {avg:+.2f}%\n"
    text += "Nganh yeu nhat:\n"
    for nganh, avg in nganh_sorted[-2:]:
        text += f"  DOWN {nganh}: {avg:+.2f}%\n"
    return text

def phan_tich_ma(symbol):
    try:
        stock = Vnstock().stock(symbol=symbol, source='VCI')
        df = stock.quote.history(start='2025-09-01', end=datetime.now().strftime('%Y-%m-%d'), interval='1D')

        if df is None or len(df) < 30:
            return f"{symbol}: Khong du du lieu", None

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

        mua_ban = lay_mua_ban_chu_dong(symbol)
        if mua_ban:
            mua_kl, ban_kl = mua_ban
            tong = mua_kl + ban_kl
            if tong > 0:
                pct_mua = (mua_kl / tong) * 100
                ket_qua += f"Mua CD: {mua_kl:,.0f} ({pct_mua:.0f}%) | Ban CD: {ban_kl:,.0f} ({100-pct_mua:.0f}%)\n"

        ket_qua += f"RSI:{rsi:.0f} MACD:{'tot' if macd_tc else 'xau'} HT:{ho_tro:,.0f}d KC:{khang_cu:,.0f}d SL:{stoploss:,.0f}d"
        return ket_qua, thay_doi

    except Exception as e:
        return f"{symbol}: Loi ({str(e)[:50]})", None

def main():
    now = datetime.now().strftime("%H:%M %d/%m/%Y")
    message = f"BAO CAO THI TRUONG - {now}\n\n"

    tong_quan, _ = get_tong_quan_thi_truong()
    message += "=== TONG QUAN THI TRUONG ===\n"
    message += tong_quan + "\n\n"

    chi_tiet_ca_phieu = ""
    ket_qua_thay_doi = {}

    for symbol in WATCHLIST:
        ket_qua, thay_doi = phan_tich_ma(symbol)
        chi_tiet_ca_phieu += ket_qua + "\n\n"
        if thay_doi is not None:
            ket_qua_thay_doi[symbol] = thay_doi
        time.sleep(3.5)

    if ket_qua_thay_doi:
        message += "=== NGANH DAN DAT ===\n"
        message += tinh_nganh_dan_dat(ket_qua_thay_doi) + "\n"

    message += "\n=== CHI TIET DANH MUC ===\n\n"
    message += chi_tiet_ca_phieu

    send_message(message)

if __name__ == "__main__":
    main()
