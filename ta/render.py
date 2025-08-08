# безоконный backend
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import traceback

from .lines import find_best_lines

def _color_for(t):
    if t in ("resistance","channel_upper","triangle_upper"): return "tab:blue"
    if t in ("support","channel_lower","triangle_lower"):   return "tab:orange"
    if t == "target": return "tab:purple"
    return "tab:gray"

def _draw_candles(ax, df):
    for i in range(len(df)):
        o, h, l, c = float(df["Open"].iloc[i]), float(df["High"].iloc[i]), float(df["Low"].iloc[i]), float(df["Close"].iloc[i])
        color = "green" if c >= o else "red"
        ax.plot([df.index[i], df.index[i]], [l, h], color=color, linewidth=1, zorder=1)
        ax.plot([df.index[i], df.index[i]], [o, c], color=color, linewidth=3, zorder=2)

def render_chart_with_lines(
    df: pd.DataFrame,
    max_lines: int = 5,
    tolerance: float = 0.01,
    min_anchors: int = 3,
    min_span: int = 20,
    zz_dev: float = 0.012,
):
    try:
        # приведение колонок
        rename = {"time":"Date","open":"Open","high":"High","low":"Low","close":"Close","volume":"Volume"}
        df = df.rename(columns=rename).copy()

        for col in ["Open","High","Low","Close"]:
            if col not in df.columns:
                raise ValueError(f"В DataFrame нет колонки {col}")

        if not isinstance(df.index, pd.DatetimeIndex):
            if "Date" in df.columns:
                df.index = pd.to_datetime(df["Date"])
            else:
                df.index = pd.to_datetime(df.index)
        df.index.name = "Date"

        # фикс high==low
        mask = df["Low"] >= df["High"]
        if mask.any():
            df.loc[mask, "High"] = df.loc[mask, "Low"] + 1e-8

        highs = df["High"].to_numpy(dtype=np.float64)
        lows  = df["Low"].to_numpy(dtype=np.float64)

        # 1-я попытка
        lines = find_best_lines(
            highs, lows,
            max_lines=int(max_lines),
            tolerance=float(tolerance),
            min_anchors=int(min_anchors),
            min_span=int(min_span),
            zz_dev=float(zz_dev),
        )
        fallback_used = False

        # авто-фолбэк: если не нашли ничего — ослабляем пороги
        if not lines:
            fallback_used = True
            lines = find_best_lines(
                highs, lows,
                max_lines=int(max_lines),
                tolerance=float(max(tolerance*2.0, 0.015)),  # +50..100%
                min_anchors=max(2, int(min_anchors)-1),
                min_span=max(8, int(min_span)-2),
                zz_dev=float(max(zz_dev*0.75, 0.004)),
            )

        fig, ax = plt.subplots(figsize=(12, 6))
        # фон (можешь менять)
        fig.patch.set_facecolor("#0d1117")
        ax.set_facecolor("#0b1015")

        _draw_candles(ax, df)

        ax.autoscale(enable=True)
        y_min, y_max = ax.get_ylim()
        n = len(df)

        def cy(y): return float(np.clip(float(y), y_min, y_max))

        counts = {}
        for L in lines:
            t = L["type"]
            counts[t] = counts.get(t, 0) + 1

            i0, i1 = int(L["i0"]), int(L["i1"])
            if not (0 <= i0 < n and 0 <= i1 < n and i1 > i0):
                continue
            m, b = float(L["slope"]), float(L["intercept"])
            x0, x1 = df.index[i0], df.index[i1]
            y0, y1 = cy(m * i0 + b), cy(m * i1 + b)
            ax.plot([x0, x1], [y0, y1], color=_color_for(t), linewidth=2.2, alpha=0.95, zorder=3)

            # якоря
            for k, y in L.get("anchors", [])[:50]:
                k = int(k)
                if 0 <= k < n:
                    ax.scatter(df.index[k], cy(y), s=12, color=_color_for(t), alpha=0.85, zorder=4)

        # оформление
        ax.set_ylabel("Price", color="#c9d1d9")
        ax.grid(True, alpha=0.12, color="#30363d")
        ax.tick_params(colors="#8b949e")
        for spine in ax.spines.values():
            spine.set_color("#30363d")

        info = {"total": sum(counts.values()), "fallback_used": fallback_used}
        info.update(counts)
        return fig, info

    except Exception:
        print("=== render_chart_with_lines ERROR ===")
        traceback.print_exc()
        raise
