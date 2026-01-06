import csv
import json
import os
from datetime import datetime

class TradeJournal:

    def __init__(self, path="trades"):
        os.makedirs(path, exist_ok=True)
        self.csv_file = f"{path}/trades.csv"
        self.json_file = f"{path}/trades.json"

        if not os.path.exists(self.csv_file):
            with open(self.csv_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "time", "symbol", "entry", "exit",
                    "qty", "pnl", "reason"
                ])

        if not os.path.exists(self.json_file):
            with open(self.json_file, "w") as f:
                json.dump([], f)

    def log(self, symbol, entry, exit_price, qty, pnl, reason):
        time = datetime.utcnow().isoformat()

        # CSV
        with open(self.csv_file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                time, symbol, entry, exit_price,
                qty, round(pnl, 4), reason
            ])

        # JSON
        with open(self.json_file, "r+") as f:
            data = json.load(f)
            data.append({
                "time": time,
                "symbol": symbol,
                "entry": entry,
                "exit": exit_price,
                "qty": qty,
                "pnl": pnl,
                "reason": reason
            })
            f.seek(0)
            json.dump(data, f, indent=2)
