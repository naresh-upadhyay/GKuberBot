
from utils.telegram import TelegramNotifier

notifier = TelegramNotifier()

notifier.send(
    f"🚀 <b>BUY</b>\n"
    f"Symbol: BTCUSDT\n"
    f"Entry: 42350\n"
    f"SL: 41920\n"
    f"TP: 43210\n"
    f"Qty: 0.012"
)