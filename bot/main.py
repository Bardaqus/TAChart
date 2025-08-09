# bot/main.py
import os
import sys
import pandas as pd
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ta.fetch import fetch_ohlcv_df
from ta.render import render_chart_with_lines
from bot.storage import add_line, list_lines, clear_lines
from bot.manual_presets import PRESET_LINES

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
BOT_TOKEN = "8481502944:AAHBRxYn_hN92snDW36e9cRJssA38xKEoDg"

LOOKBACK = {"15m": 2000, "1h": 1200}

def normalize_tf(tf: str) -> str:
    tf = (tf or "").strip().lower()
    mapping = {
        "1m":"1m","3m":"3m","5m":"5m","15m":"15m","30m":"30m",
        "1h":"1h","2h":"2h","4h":"4h","6h":"6h","8h":"8h","12h":"12h",
        "1d":"1d","3d":"3d","1w":"1w","1mo":"1M","1mth":"1M","1month":"1M"
    }
    return mapping.get(tf, "15m")

def parse_kv(args):
    out = {}
    for a in args:
        if "=" in a:
            k, v = a.split("=", 1)
            out[k.strip().lower()] = v.strip()
    return out

def _resolve_presets(df: pd.DataFrame, symbol: str, timeframe: str):
    """Преобразуем пресеты из дат в (i0,i1,slope,intercept)."""
    items = []
    key = (symbol.upper(), timeframe.lower())
    presets = PRESET_LINES.get(key, [])
    if not presets:
        return items

    dfn = df.rename(columns={"time":"Date","open":"Open","high":"High","low":"Low","close":"Close"})
    if not isinstance(dfn.index, pd.DatetimeIndex):
        if "Date" in dfn.columns:
            dfn.index = pd.to_datetime(dfn["Date"])
        else:
            dfn.index = pd.to_datetime(dfn.index)

    for p in presets:
        try:
            side = p.get("side","low").lower()
            t = p.get("type","support").lower()
            color = p.get("color","#93c5fd")
            ts0 = pd.to_datetime(p["from"])
            ts1 = pd.to_datetime(p["to"])
            i0 = int((abs(dfn.index - ts0)).argmin())
            i1 = int((abs(dfn.index - ts1)).argmin())
            if i1 <= i0:
                i0, i1 = i1, i0
            y0 = float(dfn["Low"].iloc[i0] if side=="low" else dfn["High"].iloc[i0])
            y1 = float(dfn["Low"].iloc[i1] if side=="low" else dfn["High"].iloc[i1])
            dx = (i1 - i0) or 1
            m = (y1 - y0) / dx
            b = y0 - m * i0
            items.append({"type": t, "i0": i0, "i1": i1, "slope": m, "intercept": b, "color": color})
        except Exception:
            continue
    return items

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Готов ✅\n"
        "  /chart SYMBOL TF [tol=] [anchors=] [span=] [zz=]\n"
        "  /addline SYMBOL TF type=support|resistance side=low|high from=YYYY-MM-DDTHH:MM to=YYYY-MM-DDTHH:MM [color=#hex]\n"
        "  /listlines SYMBOL TF\n"
        "  /clearlines SYMBOL TF"
    )

async def chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Использование: /chart SYMBOL TF\nНапр.: /chart BTC/USDT 1h")
        return
    symbol = context.args[0]
    timeframe = normalize_tf(context.args[1])

    tol = 0.02; anchors = 2; span = 10; zz = 0.008
    kv = parse_kv(context.args[2:])
    if "tol" in kv:
        try: tol = float(kv["tol"])
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

    limit = LOOKBACK.get(timeframe, 1200)
    await update.message.reply_text(f"⏳ {symbol} {timeframe} | bars={limit} | tol={tol} anchors={anchors} span={span} zz={zz}")

    try:
        df = await fetch_ohlcv_df(symbol, timeframe, limit)
        if not isinstance(df, pd.DataFrame) or df.empty:
            await update.message.reply_text("Пустые данные от биржи.")
            return
    except Exception as e:
        await update.message.reply_text(f"Ошибка загрузки данных: {e}")
        return

    chat_id = update.effective_chat.id
    manual_saved = list_lines(chat_id, symbol, timeframe)
    manual_presets = _resolve_presets(df, symbol, timeframe)
    manual = manual_presets + manual_saved

    try:
        fig, info = render_chart_with_lines(
            df, max_lines=7, tolerance=tol, min_anchors=anchors, min_span=span, zz_dev=zz,
            manual_lines=manual
        )
        out = "chart.png"
        fig.savefig(out, dpi=150, bbox_inches="tight")
        summary = (f"Найдено авто-линий: {info.get('total',0)} | "
                   f"res:{info.get('resistance',0)}, sup:{info.get('support',0)}, "
                   f"ch:{info.get('channel_upper',0)+info.get('channel_lower',0)}, "
                   f"tri:{info.get('triangle_upper',0)+info.get('triangle_lower',0)}")
        await update.message.reply_photo(photo=open(out, "rb"), caption=summary)
    except Exception as e:
        await update.message.reply_text(f"⚠ Ошибка при рендере: {e}")

async def addline_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Использование:\n/addline SYMBOL TF type=... side=low|high from=... to=... [color=#hex]")
        return
    symbol = context.args[0]; timeframe = normalize_tf(context.args[1]); kv = parse_kv(context.args[2:])
    t = kv.get("type","support").lower(); side = kv.get("side","low").lower(); color = kv.get("color","#93c5fd")
    if "from" not in kv or "to" not in kv:
        await update.message.reply_text("Нужно указать from= и to= в формате YYYY-MM-DD или YYYY-MM-DDTHH:MM")
        return

    limit = LOOKBACK.get(timeframe, 1200)
    try:
        df = await fetch_ohlcv_df(symbol, timeframe, limit)
        if not isinstance(df, pd.DataFrame) or df.empty:
            await update.message.reply_text("Пустые данные от биржи.")
            return
    except Exception as e:
        await update.message.reply_text(f"Ошибка загрузки данных: {e}")
        return

    df = df.rename(columns={"time":"Date","open":"Open","high":"High","low":"Low","close":"Close"})
    if not isinstance(df.index, pd.DatetimeIndex):
        if "Date" in df.columns: df.index = pd.to_datetime(df["Date"])
        else: df.index = pd.to_datetime(df.index)

    ts0 = pd.to_datetime(kv["from"]); ts1 = pd.to_datetime(kv["to"])
    i0 = int((abs(df.index - ts0)).argmin()); i1 = int((abs(df.index - ts1)).argmin())
    if i1 <= i0: i0, i1 = i1, i0
    y0 = float(df["Low"].iloc[i0] if side=="low" else df["High"].iloc[i0])
    y1 = float(df["Low"].iloc[i1] if side=="low" else df["High"].iloc[i1])
    dx = (i1 - i0) or 1; m = (y1 - y0)/dx; b = y0 - m * i0

    chat_id = update.effective_chat.id
    add_line(chat_id, symbol, timeframe, {"type": t, "i0": i0, "i1": i1, "slope": m, "intercept": b, "color": color})
    await update.message.reply_text(f"Сохранил линию: {symbol} {timeframe} [{t}] i0={i0}, i1={i1}")

async def listlines_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Использование: /listlines SYMBOL TF"); return
    symbol = context.args[0]; timeframe = normalize_tf(context.args[1])
    chat_id = update.effective_chat.id
    items = list_lines(chat_id, symbol, timeframe)
    if not items: await update.message.reply_text("Сохранённых линий нет."); return
    msg = f"Сохранённые линии ({symbol} {timeframe}):\n" + "\n".join(
        f"{i+1}) {L.get('type')} i0={L.get('i0')} i1={L.get('i1')} color={L.get('color')}" for i,L in enumerate(items)
    )
    await update.message.reply_text(msg)

async def clearlines_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2: await update.message.reply_text("Использование: /clearlines SYMBOL TF"); return
    symbol = context.args[0]; timeframe = normalize_tf(context.args[1]); chat_id = update.effective_chat.id
    cnt = clear_lines(chat_id, symbol, timeframe); await update.message.reply_text(f"Удалено линий: {cnt}")

def main():
    if not BOT_TOKEN or ":" not in BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан или неверный (.env).")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("chart", chart))
    app.add_handler(CommandHandler("addline", addline_cmd))
    app.add_handler(CommandHandler("listlines", listlines_cmd))
    app.add_handler(CommandHandler("clearlines", clearlines_cmd))
    print("🤖 Бот запущен. Жду /chart …")
    app.run_polling()

if __name__ == "__main__":
    main()
