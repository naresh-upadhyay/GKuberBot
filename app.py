from flask import Flask, render_template, request, jsonify
import json, os, random
from datetime import datetime
from uuid import uuid4

app = Flask(__name__)

# ---------------- STATIC DATA ----------------
COINS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "PEPEUSDT"]
RSI_VALUES = [20, 30, 40, 50, 60, 70, 80]

MACD = [
    {"value": "up", "label": "MACD Up"},
    {"value": "down", "label": "MACD Down"}
]

CANDLES = [
    {"value": "1m", "label": "1 Minute"},
    {"value": "5m", "label": "5 Minute"},
    {"value": "15m", "label": "15 Minute"},
    {"value": "1h", "label": "1 Hour"},
    {"value": "4h", "label": "4 Hour"},
    {"value": "1d", "label": "1 Day"}
]

STRATEGY_FILE = "strategies/saved.json"

# ---------------- HELPERS ----------------
def load_strategies():
    if not os.path.exists(STRATEGY_FILE):
        return {}
    with open(STRATEGY_FILE, "r") as f:
        return json.load(f)

def save_strategies(data):
    os.makedirs("strategies", exist_ok=True)
    with open(STRATEGY_FILE, "w") as f:
        json.dump(data, f, indent=4)

def new_strategy_id():
    return f"STRAT-{uuid4().hex[:10].upper()}"

# ---------------- ROUTES ----------------
@app.route("/")
def index():
    strategies = load_strategies()
    last_strategy = list(strategies.values())[-1] if strategies else None

    return render_template(
        "strategy.html",
        strategies=strategies,
        last_strategy=last_strategy,
        coins=COINS,
        rsi_values=RSI_VALUES,
        macd=MACD,
        candles=CANDLES
    )

@app.route("/save-strategy", methods=["POST"])
def save_strategy():
    payload = request.json
    strategies = load_strategies()

    sid = payload.get("id") or new_strategy_id()

    strategies[sid] = {
        "id": sid,
        "name": payload.get("name", f"Strategy {sid}"),
        "created_at": datetime.utcnow().isoformat(),
        "config": payload["config"]
    }

    save_strategies(strategies)

    return jsonify({"strategy_id": sid})

@app.route("/load-strategy/<sid>")
def load_strategy(sid):
    strategies = load_strategies()
    if sid not in strategies:
        return jsonify({"error": "Not found"}), 404
    return jsonify(strategies[sid])

@app.route("/start-scanner", methods=["POST"])
def start_scanner():
    cfg = request.json
    results, total_pnl = [], 0.0

    for symbol in cfg["coins"]:
        trades = random.randint(5, 20)
        wins = random.randint(0, trades)
        pnl = round(random.uniform(-100, 200), 2)
        total_pnl += pnl

        results.append({
            "symbol": symbol,
            "trades": trades,
            "wins": wins,
            "pnl": pnl
        })

    return jsonify({
        "results": results,
        "total_pnl": round(total_pnl, 2)
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
