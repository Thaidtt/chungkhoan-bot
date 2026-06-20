import os
import requests
import pandas as pd
import time
from datetime import datetime
from vnstock import Vnstock

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

NGUONG_THANH_KHOAN = 50000

DANH_SACH_QUET = [
    "VCB","ACB","CTG",
    "FPT","MWG",
    "SCS","GMD",
    "GAS","BSR","PVT","NT2",
    "DPG","HHV","PC1","KSB",
    "IDC","SZC",
    "VNM","QNS","VHC",
    "HSG",
    "SSI","HCM","FTS",
    "DHG","DBD",
    "BVH","PVI",
    "TNG",
    "DPR",
    "VOS",
    "BMP"
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
    return gan_day['low'].astype(float).min(), gan_day['high'].astype(float).max()

def quyet_dinh(rsi, macd_tich_cuc, tren_ma, gan_ho_tro, gan_khang_cu):
    if rsi < 30 and macd_tich_cuc and gan_ho_tro:
        return "MUA"
    if rsi > 70 and not macd_tich_cuc and gan_khang_cu:
        return "BAN"
    if tren_ma and macd_tich_cuc and 40 <= rsi <= 65:
        return "GIU/MUA THEM"
    if not tren_ma and not macd_tich_cuc:
        return "TRANH"
    if gan_ho_tro and macd_tich_cuc:
        return "CAN NHAC MUA"
    if gan_khang_cu and not macd_tich_cuc:
        return "CAN NHAC BAN"
    return "QUAN SAT"

def quet_ma(symbol, so_lan_thu=2):
    for lan in range(so_lan_thu):
        try:
            stock = Vnstock().stock(symbol=symbol, source='VCI')
            df = stock.quote.history(start='2025-09-01', end=datetime.now().strftime('%Y-%m-%d'), interval='1D')

            if df is None or len(df) < 30:
                return None

            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)
            closes = df['close']
            volumes = df['volume']

            kl_tb20 = volumes.tail(20).mean()
            if kl_tb20 < NGUONG_THANH_KHOAN:
                return {"symbol": symbol, "loai_tk": True}

            gia_hom_truoc = closes.iloc[-2]
            gia_dong_cua_truoc = closes.iloc[-1]

            gia_rt = lay_gia_realtime(symbol)
            la_rt = gia_rt is not None
            gia_hien_tai = gia_rt if la_rt else gia_dong_cua_truoc
            gia_so_sanh = gia_dong_cua_truoc if la_rt else gia_hom_truoc
            thay_doi = ((gia_hien_tai - gia_so_sanh) / gia_so_sanh) * 100

            rsi = tinh_rsi(closes).iloc[-1]
            macd_line, signal_line = tinh_macd(closes)
            macd_tc = macd_line.iloc[-1] > signal_line.iloc[-1]

            ma20 = closes.rolling(window=20).mean().iloc[-1]
            ma50 = closes.rolling(window=50).mean().iloc[-1]
            tren_ma = gia_hien_tai > ma20 and ma20 > ma50

            ho_tro, khang_cu = tinh_ho_tro_khang_cu(df)
            gan_ht = abs(gia_hien_tai - ho_tro) / ho_tro * 100 <= 3
            gan_kc = abs(gia_hien_tai - khang_cu) / khang_cu * 100 <= 3

            hanh_dong = quyet_dinh(rsi, macd_tc, tren_ma, gan_ht, gan_kc)

            kl_ty_le = (volumes.iloc[-1] / kl_tb20) * 100 if kl_tb20 > 0 else 0

            return {
                "symbol": symbol, "loai_tk": False, "gia": gia_hien_tai,
                "thay_doi": thay_doi, "rsi": rsi, "hanh_dong": hanh_dong,
                "kl_ty_le": kl_ty_le, "la_rt": la_rt,
                "ho_tro": ho_tro, "khang_cu": khang_cu
            }
        except Exception as e:
            if "60" in str(e) or "limit" in str(e).lower():
                time.sleep(65)
                continue
            return None
    return None

def main():
    now = datetime.now().strftime("%H:%M %d/%m/%Y")
    ket_qua = []
    bi_loai = []

    for i, symbol in enumerate(DANH_SACH_QUET):
        r = quet_ma(symbol)
        if r:
            if r.get("loai_tk"):
                bi_loai.append(symbol)
            else:
                ket_qua.append(r)
        time.sleep(1.3)

    if not ket_qua:
        send_message(f"QUET DANH MUC - {now}\n\nKhong lay duoc du lieu.")
        return

    df_kq = pd.DataFrame(ket_qua)
    co_rt = df_kq['la_rt'].any()
    nhan = "(co gia realtime)" if co_rt else "(gia dong cua gan nhat)"

    message = f"QUET DANH MUC CHAT LUONG {nhan} - {now}\n"
    message += f"(Quet {len(ket_qua)}/{len(DANH_SACH_QUET)} ma)\n\n"

    # Nhom theo hanh dong
    for nhom in ["MUA", "CAN NHAC MUA", "GIU/MUA THEM", "CAN NHAC BAN", "BAN", "TRANH", "QUAN SAT"]:
        df_nhom = df_kq[df_kq["hanh_dong"] == nhom]
        if len(df_nhom) > 0:
            message += f"=== {nhom} ({len(df_nhom)}) ===\n"
            for _, row in df_nhom.iterrows():
                message += f"{row['symbol']}: {row['gia']:,.0f}d ({row['thay_doi']:+.2f}%) RSI:{row['rsi']:.0f}\n"
            message += "\n"

    dot_bien = df_kq[df_kq["kl_ty_le"] >= 200]
    if len(dot_bien) > 0:
        message += "=== KHOI LUONG DOT BIEN ===\n"
        for _, row in dot_bien.iterrows():
            message += f"{row['symbol']}: KL {row['kl_ty_le']:.0f}% TB20\n"
        message += "\n"

    if bi_loai:
        message += f"Loai do thanh khoan: {', '.join(bi_loai)}"

    send_message(message)

if __name__ == "__main__":
    main()
