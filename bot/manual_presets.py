# bot/manual_presets.py
# Ручные линии, которые будут дорисовываться всегда.
# Ключ — (SYMBOL, TF). Индексы i0/i1 вычислим по датам при рендере.

PRESET_LINES = {
    # Пример для BTC/USDT 1h — подгони даты под свои скрины.
    ("BTC/USDT", "1h"): [
        # Верхняя диагональ (resistance по хайам)
        {
            "type": "resistance",
            "side": "high",
            "from": "2025-07-13T00:00",
            "to":   "2025-08-08T00:00",
            "color": "#c9ccd3"
        },
        # Нижняя диагональ (support по лоям)
        {
            "type": "support",
            "side": "low",
            "from": "2025-07-11T12:00",
            "to":   "2025-08-02T12:00",
            "color": "#c9ccd3"
        },
    ],

    # Пример для BTC/USDT 15m — подгони даты под свой M15-скрин.
    ("BTC/USDT", "15m"): [
        # Нисходящая верхняя граница (resistance)
        {
            "type": "resistance",
            "side": "high",
            "from": "2025-08-02T00:00",
            "to":   "2025-08-09T00:00",
            "color": "#c9ccd3"
        },
        # Растущая опора (support)
        {
            "type": "support",
            "side": "low",
            "from": "2025-08-06T06:00",
            "to":   "2025-08-09T00:00",
            "color": "#c9ccd3"
        },
        # Горизонтальная/слегка наклонная середина (если нужна)
        {
            "type": "resistance",
            "side": "high",
            "from": "2025-08-06T18:00",
            "to":   "2025-08-08T12:00",
            "color": "#c9ccd3"
        },
    ],
}
