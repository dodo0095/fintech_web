"""資料層 — yfinance 抓取與清理（api-design §2、feature-spec §5）。

⚠️ 新版 yfinance 對單一 symbol 也可能回傳 MultiIndex 欄位，
   必須統一攤平；禁止憑空假設回傳結構（company-rules 禁止憑空想像）。
"""
from __future__ import annotations

import datetime as dt

import pandas as pd
import yfinance as yf

from .constants import FRESHNESS_TOLERANCE_DAYS, MIN_ROWS

REQUIRED_COLS = ["open", "high", "low", "close", "volume"]


class DataError(Exception):
    """資料抓取或清理失敗。"""


def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    """攤平 MultiIndex 欄位為單層（取價格層 level 0）。"""
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = df.columns.get_level_values(0)
    return df


def fetch_daily(symbol: str, lookback_days: int = 90) -> pd.DataFrame:
    """抓取日線並清理為單層欄位、依日期升冪的 DataFrame。

    回傳欄位固定為 open/high/low/close/volume（小寫）。
    暖機期不足（筆數 < MIN_ROWS）則 raise DataError。
    """
    # 以日曆天推算起訖，含週末/假日緩衝，確保交易日筆數足夠暖機
    calendar_days = int(lookback_days * 1.6) + 10
    start = dt.date.today() - dt.timedelta(days=calendar_days)
    end = dt.date.today() + dt.timedelta(days=1)

    df = yf.download(
        symbol,
        start=start,
        end=end,
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=False,
    )
    if df is None or len(df) == 0:
        raise DataError(f"yfinance 無資料: {symbol}")

    df = _flatten_columns(df)
    df.columns = [str(c).lower() for c in df.columns]

    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise DataError(f"{symbol} 缺欄位 {missing}；實際欄位={list(df.columns)}")

    df = df[REQUIRED_COLS].copy()
    df["volume"] = df["volume"].fillna(0)  # 外匯/指數可能無量
    df = df.dropna(subset=["open", "high", "low", "close"]).sort_index()

    if len(df) < MIN_ROWS:
        raise DataError(
            f"{symbol} 資料筆數不足 {len(df)} < {MIN_ROWS}（暖機期不足，指標不準）"
        )
    return df


def is_fresh_today(df: pd.DataFrame, market: str, now: dt.datetime | None = None) -> bool:
    """最新資料是否夠新。

    超過容忍天數（跨週末/假日）視為「今日未開盤 / 資料過舊」，
    避免誤用舊資料當新訊號（feature-spec §5）。
    """
    if now is None:
        now = dt.datetime.now()
    latest = df.index[-1]
    latest_date = latest.date() if hasattr(latest, "date") else latest
    gap = (now.date() - latest_date).days
    return gap <= FRESHNESS_TOLERANCE_DAYS
