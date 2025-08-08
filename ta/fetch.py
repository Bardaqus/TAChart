import os
import pandas as pd
import ccxt.async_support as ccxt

async def fetch_ohlcv_df(symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
    binance = ccxt.binance({
        "apiKey": os.environ.get("BINANCE_API_KEY", ""),
        "secret": os.environ.get("BINANCE_API_SECRET", ""),
        "enableRateLimit": True,
        "options": {"defaultType": "spot"}
    })
    try:
        ohlcv = await binance.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    finally:
        await binance.close()

    # создаём DataFrame
    df = pd.DataFrame(ohlcv, columns=["time", "open", "high", "low", "close", "volume"])
    df["time"] = pd.to_datetime(df["time"], unit="ms")

    # Приводим типы к числовым
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df
