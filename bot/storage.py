import os, json
from typing import List, Dict, Any

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

def _store_path(chat_id: int) -> str:
    return os.path.join(DATA_DIR, f"{chat_id}.json")

def _load(chat_id: int) -> Dict[str, Any]:
    path = _store_path(chat_id)
    if not os.path.exists(path):
        return {"lines": []}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _save(chat_id: int, data: Dict[str, Any]):
    path = _store_path(chat_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_line(chat_id: int, symbol: str, timeframe: str, line: Dict[str, Any]):
    data = _load(chat_id)
    data.setdefault("lines", [])
    # ключ для фильтра
    line["symbol"] = symbol.upper()
    line["timeframe"] = timeframe.lower()
    data["lines"].append(line)
    _save(chat_id, data)

def list_lines(chat_id: int, symbol: str, timeframe: str) -> List[Dict[str, Any]]:
    data = _load(chat_id)
    sym = symbol.upper()
    tf = timeframe.lower()
    return [x for x in data.get("lines", []) if x.get("symbol")==sym and x.get("timeframe")==tf]

def clear_lines(chat_id: int, symbol: str, timeframe: str) -> int:
    data = _load(chat_id)
    before = len(data.get("lines", []))
    sym = symbol.upper()
    tf = timeframe.lower()
    data["lines"] = [x for x in data.get("lines", []) if not (x.get("symbol")==sym and x.get("timeframe")==tf)]
    _save(chat_id, data)
    return before - len(data["lines"])
