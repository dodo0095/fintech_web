"""技術指標（純 pandas/numpy，無外部依賴）。

所有函式輸入 pandas Series（DatetimeIndex），回傳對齊同一 index 的 Series；
暖機不足的期間為 NaN，由規則層視為「條件不成立」。
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).mean()


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    """Wilder RSI。"""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    avg_loss = loss.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - 100 / (1 + rs)
    # 無下跌 → RSI 100；無上漲也無下跌 → 50
    out = out.where(~(avg_loss == 0), 100.0)
    out = out.where(~((avg_loss == 0) & (avg_gain == 0)), 50.0)
    return out.where(avg_gain.notna())


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """回傳 (DIF, 訊號線 DEA, 柱狀體 DIF-DEA)。"""
    dif = ema(close, fast) - ema(close, slow)
    dea = dif.ewm(span=signal, adjust=False, min_periods=signal).mean()
    return dif, dea, dif - dea


def kd(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 9):
    """台灣常用 KD：RSV 以 1/3 平滑成 K，K 再以 1/3 平滑成 D，初值 50。"""
    lowest = low.rolling(n, min_periods=n).min()
    highest = high.rolling(n, min_periods=n).max()
    rng = (highest - lowest).replace(0, np.nan)
    rsv = ((close - lowest) / rng * 100).to_numpy()
    k = np.full(len(rsv), np.nan)
    d = np.full(len(rsv), np.nan)
    pk, pd_ = 50.0, 50.0
    started = False
    for i, r in enumerate(rsv):
        if np.isnan(r):
            if started:  # 區間價差為 0 → 沿用前值
                k[i], d[i] = pk, pd_
            continue
        started = True
        pk = pk * 2 / 3 + r / 3
        pd_ = pd_ * 2 / 3 + pk / 3
        k[i], d[i] = pk, pd_
    return pd.Series(k, index=close.index), pd.Series(d, index=close.index)


def bollinger(close: pd.Series, n: int = 20, k: float = 2.0):
    """回傳 (上軌, 中軌, 下軌)。"""
    mid = sma(close, n)
    std = close.rolling(n, min_periods=n).std(ddof=0)
    return mid + k * std, mid, mid - k * std


def prior_high(high: pd.Series, n: int) -> pd.Series:
    """前 N 日最高價（不含當日），用於「突破 N 日新高」。"""
    return high.shift(1).rolling(n, min_periods=n).max()


def prior_low(low: pd.Series, n: int) -> pd.Series:
    """前 N 日最低價（不含當日）。"""
    return low.shift(1).rolling(n, min_periods=n).min()


def roc(close: pd.Series, n: int) -> pd.Series:
    """N 日漲跌幅（%）。"""
    return (close / close.shift(n) - 1) * 100
