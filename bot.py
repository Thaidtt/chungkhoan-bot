python
import os
import requests
from datetime import datetime

# Lấy thông tin từ Environment Variables (sẽ cài ở Render sau)
TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_message(text):
    """Gửi tin nhắn về Telegram"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    try:
        response = requests.post(url, data=payload, timeout=10)
        print("Đã gửi:", response.status_code)
    except Exception as e:
        print("Lỗi gửi tin:", e)

def get_my_chat_id():
    """Dùng để lấy Chat ID nếu chưa có - chạy 1 lần rồi xóa"""
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    response = requests.get(url, timeout=10)
    print(response.json())

def main():
    now = datetime.now().strftime("%H:%M %d/%m/%Y")
    message = f"🤖 Bot đã chạy thành công lúc {now}\n\nĐây là tin nhắn test đầu tiên từ hệ thống theo dõi chứng khoán."
    send_message(message)

if __name__ == "__main__":
    main()
