import os
import requests
import pandas as pd
import time
from datetime import datetime
from vnstock import Vnstock

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

NGUONG_THANH_KHOAN = 50000  # co phieu/ngay

DANH_SACH_QUET = [
    "VCB","ACB","CTG","MBB","HDB","BID","TCB",
    "FPT","MWG","PNJ","FRT",
    "SCS","GMD","HAH","VSC",
    "GAS","BSR","PVT","NT2","PVS","REE","POW",
    "DPG","HHV","PC1","KSB","LCG",
    "IDC","SZC","HDC","NLG",
    "VNM","QNS","VHC","DBC",
    "HSG","HPG","NKG",
    "SSI","HCM","FTS","VCI",
    "DHG","DBD","IMP",
    "BVH","PVI",
    "TNG","MSH","TCM",
    "DPR","PHR",
    "VOS",
    "CMG","BMP","VCS",
    "FMC"
]

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    try:
        response = requests.post(url, data=payload, timeout=15)
        print("Da gui:", response.status_code)
    except Exception as e:
        print("Loi gui tin:", e)

def quet_ma(symbol):
    try:
        stock = Vnstock().stock(symbol=symbol, source='VCI')
        df = stock.quote.history(start='2026-04-01', end=datetime.now().strftime('%Y-%m-%d'), interval='1D')

        if df is None or len(df) < 21:
            return None

        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(float)
        closes = df['close']
        volumes = df['volume']

        gia_hom_nay = closes.iloc[-1]
        gia_hom_truoc = closes.iloc[-2]
        thay_doi = ((gia_hom_nay - gia_hom_truoc) / gia_hom_truoc) * 100

        kl_tb20 = volumes.tail(20).mean()

        # Loc thanh khoan ngay tai day
        if kl_tb20 < NGUONG_THANH_KHOAN:
            return {"symbol": symbol, "loai_thanh_khoan": True, "kl_tb20": kl_tb20}

        kl_hom_nay = volumes.iloc[-1]
        kl_ty_le = (kl_hom_nay / kl_tb20) * 100 if kl_tb20 > 0 else 0

        return {
            "symbol": symbol,
            "gia": gia_hom_nay,
            "thay_doi": thay_doi,
            "kl_ty_le": kl_ty_le,
            "kl_tb20": kl_tb20,
            "loai_thanh_khoan": False
        }
    except Exception as e:
        print(f"Loi quet {symbol}: {e}")
        return None

def main():
    now = datetime.now().strftime("%H:%M %d/%m/%Y")
    ket_qua = []
    bi_loai = []

    for symbol in DANH_SACH_QUET:
        r = quet_ma(symbol)
        if r:
            if r.get("loai_thanh_khoan"):
                bi_loai.append(f"{r['symbol']} (KL TB20: {r['kl_tb20']:,.0f})")
            else:
                ket_qua.append(r)
        time.sleep(0.5)

    if not ket_qua:
        send_message(f"QUET DANH MUC CHAT LUONG - {now}\n\nKhong lay duoc du lieu.")
        return

    df_kq = pd.DataFrame(ket_qua)

    top_tang = df_kq.sort_values("thay_doi", ascending=False).head(5)
    top_giam = df_kq.sort_values("thay_doi", ascending=True).head(5)
    dot_bien = df_kq[df_kq["kl_ty_le"] >= 200].sort_values("kl_ty_le", ascending=False).head(10)

    message = f"QUET DANH MUC CHAT LUONG - {now}\n"
    message += f"(Da quet {len(ket_qua)}/{len(DANH_SACH_QUET)} ma dat thanh khoan)\n\n"

    message += "=== TOP TANG MANH ===\n"
    for _, row in top_tang.iterrows():
        message += f"UP {row['symbol']}: {row['gia']:,.0f}d ({row['thay_doi']:+.2f}%)\n"

    message += "\n=== TOP GIAM MANH ===\n"
    for _, row in top_giam.iterrows():
        message += f"DOWN {row['symbol']}: {row['gia']:,.0f}d ({row['thay_doi']:+.2f}%)\n"

    if len(dot_bien) > 0:
        message += "\n=== KHOI LUONG DOT BIEN (>200% TB20) ===\n"
        for _, row in dot_bien.iterrows():
            message += f"{row['symbol']}: KL {row['kl_ty_le']:.0f}% TB20, gia {row['thay_doi']:+.2f}%\n"

    if bi_loai:
        message += f"\n=== LOAI DO THANH KHOAN THAP (<{NGUONG_THANH_KHOAN:,}cp/ngay) ===\n"
        message += ", ".join([b.split(" (")[0] for b in bi_loai])

    send_message(message)

if __name__ == "__main__":
    main()
