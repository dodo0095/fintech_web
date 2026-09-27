"""行情資料層：yfinance（還原權息）＋ SQLite 快取。

- 每檔抓完整歷史（period=max）存進 PriceCache；超過 CACHE_HOURS 才重抓。
- 重抓失敗但有舊快取 → 用舊資料並回報 stale=True，不讓整個回測失敗。
- 同一檔同時被多人請求時只打一次 Yahoo（per-symbol lock）。
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import timedelta

import pandas as pd
from django.utils import timezone

from .models import PriceCache

log = logging.getLogger(__name__)

CACHE_HOURS = 6
MIN_ROWS = 30
REQUIRED = ["open", "high", "low", "close", "volume"]

_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


class PriceError(Exception):
    """抓不到可用行情（訊息可直接給使用者看）。"""


def _lock_for(symbol: str) -> threading.Lock:
    with _locks_guard:
        lk = _locks.get(symbol)
        if lk is None:
            lk = _locks[symbol] = threading.Lock()
        return lk


def _download(symbol: str) -> pd.DataFrame:
    """從 Yahoo 抓完整日線；回傳小寫欄位 DataFrame，失敗回傳空 DataFrame。"""
    import yfinance as yf  # 延遲 import：測試與啟動不必載入

    df = yf.download(
        symbol,
        period="max",
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=False,
    )
    if df is None or len(df) == 0:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):  # 新版 yfinance 單檔也可能是 MultiIndex
        df = df.copy()
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).lower() for c in df.columns]
    if any(c not in df.columns for c in REQUIRED):
        log.warning("yfinance %s 欄位不足：%s", symbol, list(df.columns))
        return pd.DataFrame()
    df = df[REQUIRED].copy()
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    df["volume"] = df["volume"].fillna(0)
    df = df.dropna(subset=["open", "high", "low", "close"])
    df = df[(df["close"] > 0) & (df["open"] > 0)]
    df = df[~df.index.duplicated(keep="last")].sort_index()
    return df


def _to_payload(df: pd.DataFrame) -> str:
    return json.dumps({
        "d": [d.strftime("%Y-%m-%d") for d in df.index],
        "o": [round(float(x), 4) for x in df["open"]],
        "h": [round(float(x), 4) for x in df["high"]],
        "l": [round(float(x), 4) for x in df["low"]],
        "c": [round(float(x), 4) for x in df["close"]],
        "v": [int(x) for x in df["volume"]],
    }, separators=(",", ":"))


def _from_payload(text: str) -> pd.DataFrame:
    p = json.loads(text)
    return pd.DataFrame(
        {"open": p["o"], "high": p["h"], "low": p["l"], "close": p["c"], "volume": p["v"]},
        index=pd.to_datetime(p["d"]),
        dtype=float,
    )


def get_prices(symbol: str, downloader=None) -> tuple[pd.DataFrame, dict]:
    """回傳 (日線 DataFrame, 資訊 {symbol, updated_at, stale})。抓不到丟 PriceError。"""
    downloader = downloader or _download
    with _lock_for(symbol):
        row = PriceCache.objects.filter(symbol=symbol).first()
        now = timezone.now()
        if row and now - row.updated_at < timedelta(hours=CACHE_HOURS):
            return _from_payload(row.payload), {"symbol": symbol, "updated_at": row.updated_at, "stale": False}

        try:
            df = downloader(symbol)
        except Exception as exc:  # 網路、Yahoo 限流等
            log.warning("yfinance %s 失敗：%s", symbol, exc)
            df = pd.DataFrame()

        if len(df) >= MIN_ROWS:
            PriceCache.objects.update_or_create(
                symbol=symbol,
                defaults={
                    "updated_at": now,
                    "first_date": df.index[0].date(),
                    "last_date": df.index[-1].date(),
                    "rows": len(df),
                    "payload": _to_payload(df),
                },
            )
            return df, {"symbol": symbol, "updated_at": now, "stale": False}

        if row:  # 重抓失敗 → 退回舊快取
            return _from_payload(row.payload), {"symbol": symbol, "updated_at": row.updated_at, "stale": True}
        raise PriceError(f"抓不到 {symbol} 的歷史股價（Yahoo 無資料或暫時無法連線）")


def get_prices_any(candidates: list[str], downloader=None) -> tuple[pd.DataFrame, dict]:
    """依序嘗試多個 Yahoo 代號（例如 .TW／.TWO），回傳第一個有資料的。"""
    last_err = None
    for sym in candidates:
        try:
            return get_prices(sym, downloader=downloader)
        except PriceError as exc:
            last_err = exc
    raise last_err or PriceError("沒有可嘗試的代號")
