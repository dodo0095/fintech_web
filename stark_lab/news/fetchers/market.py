"""市場總覽（大盤 + 台積電 ADR）→ market payload（自 fetch_market.py 移植）。"""
from __future__ import annotations

from datetime import datetime

from .common import TW, now_iso, safe_float

INDICES = [
    ("道瓊", "^DJI"),
    ("納斯達克", "^IXIC"),
    ("S&P 500", "^GSPC"),
    ("台積電 ADR", "TSM"),
]

TW_INDICES = [
    ("加權指數", "^TWII"),
    ("櫃買指數", "^TWOII"),
    ("元大台灣50", "0050.TW"),
    ("台積電", "2330.TW"),
]


def fetch_quote(symbol: str) -> dict:
    """取得報價與漲跌幅。

    NOTE: 漲跌幅基準一律採 history 最近兩根收盤價，不用 fast_info.previous_close。
    該欄位對部分海外掛牌（如台積電 ADR TSM）曾回傳與實際收盤不符的髒值
    （實測 412.77，正確應為前一交易日收盤附近），導致漲跌幅誤算超過 2 個百分點。
    history 的收盤序列（含當日即時更新的最後一根）沒有這個問題，四大指數 +
    ADR + 0050 + 2330 實測皆正確，一併修掉 2330.TW 先前的小數點誤差。
    """
    import yfinance as yf

    t = yf.Ticker(symbol)
    hist = t.history(period="5d")
    if hist is None or hist.empty:
        raise RuntimeError("no history for {}".format(symbol))
    closes = hist["Close"].dropna()
    if closes.empty:
        raise RuntimeError("empty close for {}".format(symbol))
    price = safe_float(closes.iloc[-1])
    prev = safe_float(closes.iloc[-2]) if len(closes) >= 2 else price

    if price is None:
        raise RuntimeError("no price for {}".format(symbol))
    if prev is None or prev == 0:
        change = change_pct = 0.0
    else:
        change = round(price - prev, 4)
        change_pct = round((price - prev) / prev * 100, 4)

    return {"value": round(price, 4), "change": change, "change_pct": change_pct}


def fetch_group(pairs):
    items, errors = [], []
    for name, symbol in pairs:
        try:
            q = fetch_quote(symbol)
            items.append({"name": name, "symbol": symbol, **q})
            print("  {} ({}): {} ({}%)".format(name, symbol, q["value"], q["change_pct"]))
        except Exception as e:
            errors.append("{}: {}".format(symbol, e))
            print("  [warn] {} ({}): {}".format(name, symbol, e))
    return items, errors


def build() -> dict:
    """回傳 market payload（等同原 market.json 內容）。全部失敗則丟例外。"""
    items, errors = fetch_group(INDICES)
    tw_items, tw_errors = fetch_group(TW_INDICES)

    if not items and not tw_items:
        raise RuntimeError("all market quotes failed")

    h = datetime.now(TW).hour
    if h < 8:
        session = "pre-tw-open"
    elif h < 21:
        session = "pre-us-open"
    else:
        session = "us-session"

    try:
        tsm = next((x for x in items if x.get("symbol") == "TSM"), None)
        tw = next((x for x in tw_items if x.get("symbol") == "2330.TW"), None)
        if tsm and tw and tw.get("value"):
            fx = None
            try:
                fx = fetch_quote("USDTWD=X")["value"]
            except Exception as e:
                print("  [warn] USDTWD=X: {}".format(e))
            if fx:
                implied = tsm["value"] * fx / 5.0
                prem = (implied / tw["value"] - 1) * 100
                tw["note"] = "ADR {} {:+.1f}%".format("溢價" if prem >= 0 else "折價", prem)
    except Exception as e:
        print("  [warn] ADR premium: {}".format(e))

    payload = {
        "updated_at": now_iso(),
        "session": session,
        "indices": items,
        "tw_indices": tw_items,
    }
    errs = errors + tw_errors
    if errs:
        payload["partial_errors"] = errs
    return payload
