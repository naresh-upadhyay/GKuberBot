import csv
import json
import os
from datetime import datetime, UTC

class TradeJournal:
    def __init__(self, path="trades"):
        os.makedirs(path, exist_ok=True)

        self.csv_file = os.path.join(path, "trades.csv")
        self.json_file = os.path.join(path, "trades.json")

        # CSV init
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "time", "symbol", "entry", "exit",
                    "qty", "pnl", "reason"
                ])

        # JSON init
        if not os.path.exists(self.json_file):
            with open(self.json_file, "w", encoding="utf-8") as f:
                json.dump([], f)

    def _read_json(self):
        try:
            with open(self.json_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _write_json(self, data):
        with open(self.json_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def log(self, symbol, entry, exit_price, qty, pnl, reason):
        time = datetime.now(UTC).isoformat()

        # CSV
        with open(self.csv_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                time, symbol, entry, exit_price,
                qty, round(float(pnl), 4), reason
            ])

        # JSON (SAFE)
        data = self._read_json()
        data.append({
            "time": time,
            "symbol": symbol,
            "entry": entry,
            "exit": exit_price,
            "qty": qty,
            "pnl": float(pnl),
            "reason": reason
        })
        self._write_json(data)


"""
journal = TradeJournal()
journal.log(
            "symbol", "trade.entry", "price", "trade.qty", 0.40, "reason"
        )
"""