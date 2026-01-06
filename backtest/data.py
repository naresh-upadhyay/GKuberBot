import pandas as pd

def load_csv(path: str):
    """
    CSV format:
    timestamp, open, high, low, close, volume
    """
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df
