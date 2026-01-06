import requests
from config import config


class TelegramNotifier:

    def __init__(self):
        self.token = config.telegram.TELEGRAM_BOT_TOKEN
        self.chat_id = config.telegram.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}/sendMessage"

    def send(self, message: str):
        if not self.token or not self.chat_id:
            return

        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML"
        }

        try:
            requests.post(self.base_url, data=payload, timeout=5)
        except Exception as e:
            print(f"Telegram error: {e}")

"""
notifier = TelegramNotifier()
notifier.send(
    f"🚀 <b>BUY</b>\n"
    f"Symbol: PREPUSDT\n"
    f"Entry: 42350\n"
    f"SL: 41920\n"
    f"TP: 43210\n"
    f"Qty: 0.012"
)"""