import os
import sys
import pandas as pd
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# чтобы работали импорты пакетов из корня (ta/, bot/)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ta.fetch import fetch_ohlcv_df
from ta.render import render_chart_with_lines

# .env из корня
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
BOT_TOKEN = "8481502944:AAHBRxYn_hN92snDW36e9cRJssA38xKEoDg"

def normalize_tf(tf: str) -> str:
    tf = (tf or "").strip().lower()
    mapping = {
        "1m":"1m","3m":"3m","5m":"5m","15m":"15m","30m":"30m",
        "1h":"1h","2h":"2h","4h":"4h","6h":"6h","8h":"8h","12h":"12h",
        "1d":"1d","3d":"3d","1w":"1w","1mo":"1M","1mth":"1M","1month":"1M"
    }
    if tf.isdigit():
        mins = int(tf)
        return f"{mins}m" if mins < 60 else f"{mins//60}h"
    return mapping.get(tf, "15m")

def parse_kv(args):
    out = {}
    for a in args:
        if "=" in a:
            k, v = a.split("=", 1)
            out[k.strip().lower()] = v.strip()
    return out

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Готов ✅\n"
        "Формат: /chart SYMBOL TF BARS LINES [tol=] [anchors=] [span=] [zz=]\n"
        "Напр.: /chart BTC/USDT 15m 800 7 tol=0.02 anchors=2 span=10 zz=0.008"
    )

async def chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # мягкие дефолты, чтобы линии находились чаще
    symbol = "BTC/USDT"
    timeframe = "15m"
    limit = 500
    max_lines = 7
    tol = 0.02        # 2%
    anchors = 2
    span = 10
    zz = 0.008        # 0.8%

    # позиционные
    if len(context.args) >= 1: symbol = context.args[0]
    if len(context.args) >= 2: timeframe = normalize_tf(context.args[1])
    if len(context.args) >= 3:
        try: limit = int(context.args[2])
        except: pass
    if len(context.args) >= 4:
        try: max_lines = int(context.args[3])
        except: pass

    # ключ=значение
    kv = parse_kv(context.args[4:])
    if "tol" in kv:
        try: tol = float(kv["tol"]); 
        except: pass
    if "anchors" in kv:
        try: anchors = int(kv["anchors"])
        except: pass
    if "span" in kv:
        try: span = int(kv["span"])
        except: pass
    if "zz" in kv:
        try: zz = float(kv["zz"])
        except: pass

    await update.message.reply_text(
        f"⏳ {symbol} {timeframe} | bars={limit} | lines={max_lines}\n"
        f"Параметры: tol={tol}, anchors={anchors}, span={span}, zz={zz}"
    )

    # загрузка
    try:
        df = await fetch_ohlcv_df(symbol, timeframe, limit)
        if not isinstance(df, pd.DataFrame) or df.empty:
            await update.message.reply_text("Пустые данные от биржи.")
            return
    except Exception as e:
        await update.message.reply_text(f"Ошибка загрузки данных: {e}")
        return

    # рендер
    try:
        fig, info = render_chart_with_lines(
            df,
            max_lines=max_lines,
            tolerance=tol,
            min_anchors=anchors,
            min_span=span,
            zz_dev=zz
        )
        summary = (
            f"Найдено линий: {info.get('total',0)}"
            f" | res: {info.get('resistance',0)}"
            f" | sup: {info.get('support',0)}"
            f" | ch: {info.get('channel_upper',0)+info.get('channel_lower',0)}"
            f" | tri: {info.get('triangle_upper',0)+info.get('triangle_lower',0)}"
            f" | target: {info.get('target',0)}"
        )
        if info.get("fallback_used"):
            summary += "  (использован авто-фолбэк параметров)"
        await update.message.reply_text(summary)

        out = "chart.png"
        fig.savefig(out, dpi=150, bbox_inches="tight")
        await update.message.reply_photo(photo=open(out, "rb"),
                                         caption=f"{symbol} {timeframe} | bars={limit} | lines={max_lines}")
    except Exception as e:
        await update.message.reply_text(f"⚠ Ошибка при рендере: {e}")

def main():
    if not BOT_TOKEN or ":" not in BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан или неверный (.env в корне).")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("chart", chart))
    print("🤖 Бот запущен. Жду /chart")
    app.run_polling()

if __name__ == "__main__":
    main()
