TA Lines Telegram Bot (Binance) — Clean Mac Version

This bot fetches OHLCV from Binance and returns a PNG chart
with ONLY lines drawn by strict rules:
  - Lines start/end exactly on candle highs OR lows
  - Each line has >= 3 anchor candles (all highs OR all lows)
  - Prefer longer span

Quick start (macOS + Python 3.10):
1) Install Python 3.10 from python.org
2) Open Terminal, cd into this folder
3) python3.10 -m pip install -r requirements.txt
4) Edit .env (put your Telegram bot token)
5) python3.10 bot/main.py

Telegram commands:
- /start
- /chart
- /chart BTC/USDT 1h 800 7
