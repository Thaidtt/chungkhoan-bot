import os
import requests
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

def get_stock_report():
    lines = []
    canh_bao = []
    for symbol in WATCHLIST:
        try:
            stock = Vnstock().stock(symbol=symbol, source='VCI')
            df = stock.quote.history(start='2026-01-01', end=datetime.now().strftime('%Y-%m-%d'), interval='1D')
            if df is None or len(df) < 2:
                lines.append(f"{symbol}: Khong co du lieu")
                continue
            gia_hom_nay = df.iloc[-1]['close']
            gia_hom_truoc = df.iloc[-2]['close']
            thay_doi = ((gia_hom_nay - gia_hom_truoc) / gia_hom_truoc) * 100
            dau = "UP" if thay_doi >= 0 else "DOWN"
            lines.append(f"{dau} {symbol}: {gia_hom_nay:,.0f}d ({thay_doi:+.2f}%)")
            if abs(thay_doi) >= 3:
                canh_bao.append(f"CANH BAO {symbol}: {thay_doi:+.2f}%")
        except Exception as e:
            lines.append(f"{symbol}: Loi ({str(e)[:30]})")
    return lines, canh_bao

def main():
    now = datetime.now().strftime("%H:%M %d/%m/%Y")
    lines, canh_bao = get_stock_report()

    message = f"BAO CAO DANH MUC - {now}\n\n"
    message += "\n".join(lines)

    if canh_bao:
        message += "\n\nCANH BAO:\n" + "\n".join(canh_bao)

    send_message(message)

if __name__ == "__main__":
    main()
