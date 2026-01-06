import os

class TelegramConfig:
    def __init__(self):
        self.TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

    def as_dict(self):
        return {
            "bot_token": self.TELEGRAM_BOT_TOKEN,
            "chat_id": self.TELEGRAM_CHAT_ID
        }
