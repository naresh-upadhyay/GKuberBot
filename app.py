from flask import Flask, render_template, request, jsonify
import os, json, random
from uuid import uuid4
from backtest.engine import MultiCoinBacktester

app = Flask(__name__)
STRATEGY_FILE = "strategies/saved.json"

# ---------------- STATIC DATA ----------------
COINS = [
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","ADAUSDT",
    "DOGEUSDT","TRXUSDT","AVAXUSDT","LINKUSDT",
    "PEPEUSDT","SHIBUSDT","FLOKIUSDT","BONKUSDT",
    "UNIUSDT","AAVEUSDT","COMPUSDT","MKRUSDT","SNXUSDT"
]

RSI_VALUES = [20,30,40,50,60,70,80]

MACD = [
    {"value":"up","label":"MACD Up"},
    {"value":"down","label":"MACD Down"}
]

CANDLES = [
    {"value":"1m","label":"1 Minute"},
    {"value":"5m","label":"5 Minute"},
    {"value":"15m","label":"15 Minute"},
    {"value":"1h","label":"1 Hour"},
    {"value":"4h","label":"4 Hour"},
    {"value":"1d","label":"1 Day"},
]

# ---------------- HELPERS ----------------
def load_strategies():
    if not os.path.exists(STRATEGY_FILE):
        return {}
    with open(STRATEGY_FILE) as f:
        return json.load(f)

def save_strategies(data):
    os.makedirs("strategies", exist_ok=True)
    with open(STRATEGY_FILE,"w") as f:
        json.dump(data,f,indent=4)

# ---------------- ROUTES ----------------
@app.route("/")
def index():
    strategies = load_strategies()
    last_strategy = list(strategies.values())[-1] if strategies else None
    return render_template(
        "strategy.html",
        coins=COINS,
        rsi_values=RSI_VALUES,
        macd=MACD,
        candles=CANDLES,
        strategies=strategies,
        last_strategy=last_strategy
    )

@app.route("/save-strategy", methods=["POST"])
def save_strategy():
    p = request.json
    strategies = load_strategies()
    sid = p.get("id") or f"STRAT-{uuid4().hex[:10].upper()}"
    strategies[sid] = {"id":sid,"name":p["name"],"config":p["config"]}
    save_strategies(strategies)
    return jsonify({"strategy_id":sid})

@app.route("/load-strategy/<sid>")
def load_strategy(sid):
    return jsonify(load_strategies().get(sid))

@app.route("/delete-strategy/<sid>", methods=["DELETE"])
def delete_strategy(sid):
    strategies = load_strategies()
    if sid in strategies:
        del strategies[sid]
        save_strategies(strategies)
    return jsonify({"status":"deleted"})

@app.route("/export-strategy/<sid>")
def export_strategy(sid):
    return jsonify(load_strategies().get(sid))

@app.route("/start-scanner", methods=["POST"])
def start_scanner():
    cfg = request.json
    res, total = [], 0
    for c in cfg["coins"]:
        trades = random.randint(5,15)
        wins = random.randint(0,trades)
        pnl = round(random.uniform(-100,200),2)
        total += pnl
        res.append({"symbol":c,"trades":trades,"wins":wins,"pnl":pnl})
    return jsonify({"results":res,"total_pnl":round(total,2)})

@app.route("/run-backtest", methods=["POST"])
def run_backtest():
    cfg = request.json
    bt = MultiCoinBacktester(
        symbols=cfg["coins"],
        interval=cfg["buy"]["candle"],
        start_date=cfg["date_range"]["from"],
        end_date=cfg["date_range"]["to"],
    )
    return jsonify(bt.run())

# ===================== MAIN =====================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
