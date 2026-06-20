import os
import requests
import pandas as pd
import time
from datetime import datetime
from vnstock import Vnstock

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

DANH_SACH_QUET = [
    # Ngan hang
    "VCB","ACB","CTG",
    # Cong nghe - Ban le
    "FPT","MWG",
    # Ha tang - Cang
    "SCS","GMD",
    # Nang luong - Dau khi
    "GAS","BSR","PVT","NT2",
    # Xay dung - Dau tu cong
    "DPG","HHV","PC1","KSB",
    # Bat dong san
    "IDC","SZC",
    # Tieu dung - Thuc pham
    "VNM","QNS","VHC",
    # Vat lieu - Hoa chat
    "HSG",
    # Chung khoan
    "SSI","HCM","FTS",
    # Duoc pham
    "DHG","DBD",
    # Bao hiem
    "BVH","PVI",
    # Det may
    "TNG",
    # Cao su
    "DPR",
    # Van tai bien
    "VOS",
    # Cong nghe khac
    "BMP"
]

NGUONG_THANH_KHOAN = 50000

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    try:
        response = requests.post(url, data=payload, timeout=15)
        print("Da gui:", response.status_code)
    except Exception as e:
        print("Loi gui tin:", e)

def quet_ma(symbol, so_lan_thu=3):
    for lan in range(so_lan_thu):
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
            loi_str = str(e)
            if "rate" in loi_str.lower() or "60" in loi_str or "limit" in loi_str.lower():
                print(f"{symbol}: Rate limit, cho 65 giay roi thu lai (lan {lan+1}/{so_lan_thu})")
                time.sleep(65)
                continue
            else:
                print(f"Loi quet {symbol}: {e}")
                return None
    print(f"{symbol}: Bo qua sau {so_lan_thu} lan thu")
    return None

def main():
    now = datetime.now().strftime("%H:%M %d/%m/%Y")
    ket_qua = []
    bi_loai = []

    for i, symbol in enumerate(DANH_SACH_QUET):
        r = quet_ma(symbol)
        if r:
            if r.get("loai_thanh_khoan"):
                bi_loai.append(r['symbol'])
            else:
                ket_qua.append(r)

        # Nghi 1.5s giua moi ma, nghi them sau moi 40 ma de tranh cham rate limit
        time.sleep(1.5)
        if (i + 1) % 40 == 0:
            print(f"Da quet {i+1} ma, nghi 30s de bao toan rate limit...")
            time.sleep(30)

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
        message += f"\n=== LOAI DO THANH KHOAN THAP ===\n"
        message += ", ".join(bi_loai)

    send_message(message)

if __name__ == "__main__":
    main()
