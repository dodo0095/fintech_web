"""績效指標計算。"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def _r(v, nd=2):
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return round(f, nd) if math.isfinite(f) else None


def curve_stats(equity: np.ndarray, dates: pd.DatetimeIndex) -> dict:
    """權益曲線的報酬／風險指標（百分比數字，例如 12.3 代表 12.3%）。"""
    eq = np.asarray(equity, dtype=float)
    if len(eq) < 2 or not eq[0]:
        return {}
    total = eq[-1] / eq[0] - 1
    days = max((dates[-1] - dates[0]).days, 1)
    years = days / 365.25
    cagr = (eq[-1] / eq[0]) ** (1 / years) - 1 if eq[-1] > 0 and years > 0 else -1.0
    peak = np.maximum.accumulate(eq)
    dd = eq / peak - 1
    mdd_i = int(dd.argmin())
    peak_i = int(eq[: mdd_i + 1].argmax())
    rets = np.diff(eq) / eq[:-1]
    std = rets.std(ddof=1) if len(rets) > 1 else 0.0
    sharpe = rets.mean() / std * math.sqrt(TRADING_DAYS) if std > 0 else None
    vol = std * math.sqrt(TRADING_DAYS)
    calmar = cagr / abs(dd.min()) if dd.min() < 0 else None
    return {
        "total_return": _r(total * 100),
        "cagr": _r(cagr * 100),
        "max_drawdown": _r(dd.min() * 100),
        "mdd_peak_date": dates[peak_i].strftime("%Y-%m-%d"),
        "mdd_trough_date": dates[mdd_i].strftime("%Y-%m-%d"),
        "volatility": _r(vol * 100),
        "sharpe": _r(sharpe),
        "calmar": _r(calmar),
        "final_equity": _r(eq[-1], 0),
    }


def trade_stats(trades: list[dict], position: np.ndarray) -> dict:
    n = len(trades)
    exposure = float(np.mean(position)) * 100 if len(position) else 0.0
    if not n:
        return {"trades": 0, "exposure": _r(exposure)}
    rets = np.array([t["return_pct"] for t in trades], dtype=float)
    pnls = np.array([t["pnl"] for t in trades], dtype=float)
    wins = pnls[pnls > 0]
    losses = pnls[pnls <= 0]
    max_streak = streak = 0
    for p in pnls:
        streak = streak + 1 if p <= 0 else 0
        max_streak = max(max_streak, streak)
    pf = wins.sum() / abs(losses.sum()) if losses.sum() < 0 else None
    return {
        "trades": n,
        "win_rate": _r(len(wins) / n * 100),
        "avg_return": _r(rets.mean()),
        "avg_win": _r(rets[pnls > 0].mean()) if len(wins) else None,
        "avg_loss": _r(rets[pnls <= 0].mean()) if len(losses) else None,
        "best_trade": _r(rets.max()),
        "worst_trade": _r(rets.min()),
        "profit_factor": _r(pf),
        "avg_hold_days": _r(np.mean([t["hold_days"] for t in trades]), 1),
        "max_consecutive_losses": int(max_streak),
        "exposure": _r(exposure),
    }


def yearly_returns(series: dict[str, np.ndarray], dates: pd.DatetimeIndex) -> list[dict]:
    """各年度報酬（%），series 為 {名稱: 權益或價格序列}。"""
    df = pd.DataFrame({k: np.asarray(v, float) for k, v in series.items()}, index=dates)
    out = []
    prev_end = df.iloc[0]
    for year, g in df.groupby(df.index.year):
        end = g.iloc[-1]
        row = {"year": int(year)}
        for k in series:
            base = prev_end[k]
            row[k] = _r((end[k] / base - 1) * 100) if base and math.isfinite(base) else None
        out.append(row)
        prev_end = end
    return out
