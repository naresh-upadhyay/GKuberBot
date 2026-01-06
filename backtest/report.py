import numpy as np

def generate_report(trades, initial_balance, final_balance):
    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t < 0]

    return {
        "Initial Balance": initial_balance,
        "Final Balance": final_balance,
        "Total Trades": len(trades),
        "Win Rate %": round(len(wins) / len(trades) * 100, 2) if trades else 0,
        "Profit Factor": round(abs(sum(wins) / sum(losses)), 2) if losses else "∞",
        "Max Loss": round(min(trades), 2) if trades else 0
    }
