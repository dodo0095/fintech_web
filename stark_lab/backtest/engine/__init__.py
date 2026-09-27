"""回測引擎：純函式、不碰 Django 與網路，方便單元測試。

入口：run_backtest(df, strategy, settings, start, end, benchmark=None)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .metrics import curve_stats, trade_stats, yearly_returns
from .rules import (  # noqa: F401 re-export
    INDICATORS,
    OPERATORS,
    RISK_FIELDS,
    StrategyError,
    build_signals,
    describe_strategy,
    validate_strategy,
    warmup_days,
)
from .simulator import Settings, simulate

MIN_BARS = 20
MAX_POINTS = 1500  # 回傳給前端的曲線點數上限（超過就抽樣）


def _downsample_idx(n: int) -> np.ndarray:
    if n <= MAX_POINTS:
        return np.arange(n)
    idx = np.linspace(0, n - 1, MAX_POINTS).round().astype(int)
    return np.unique(idx)


def run_backtest(
    df: pd.DataFrame,
    strategy: dict,
    settings: Settings,
    start: pd.Timestamp,
    end: pd.Timestamp,
    benchmark: pd.Series | None = None,
    benchmark_label: str = "0050",
) -> dict:
    """df：完整日線（含暖機期），strategy 需先 validate_strategy。

    benchmark：大盤比較用收盤價序列（可 None）。
    """
    df = df.sort_index()
    df = df[df.index <= end]
    entry, exit_ = build_signals(df, strategy)
    in_range = np.flatnonzero(df.index >= start)
    if len(in_range) < MIN_BARS:
        raise StrategyError(f"回測區間內交易日太少（{len(in_range)} 天），請拉長區間")
    start_idx = int(in_range[0])

    sim = simulate(df, entry, exit_, strategy["risk"], settings, start_idx=start_idx)
    dates = df.index[start_idx:]
    equity = sim["equity"]

    # 買進持有（同一檔、同樣成本假設的簡化版：首日開盤買、不計後續成本）
    close = df["close"].to_numpy(float)[start_idx:]
    first_open = float(df["open"].iloc[start_idx]) or close[0]
    bh = settings.capital * close / first_open

    series = {"strategy": equity, "buy_hold": bh}
    bench_curve = None
    if benchmark is not None and len(benchmark):
        b = benchmark.sort_index().reindex(dates).ffill().bfill()
        if b.notna().all() and float(b.iloc[0]) > 0:
            bench_curve = settings.capital * b.to_numpy(float) / float(b.iloc[0])
            series["benchmark"] = bench_curve

    stats = {
        "strategy": curve_stats(equity, dates),
        "buy_hold": curve_stats(bh, dates),
    }
    if bench_curve is not None:
        stats["benchmark"] = curve_stats(bench_curve, dates)
    stats["strategy"].update(trade_stats(sim["trades"], sim["position"]))

    # 曲線（抽樣）＋回撤
    idx = _downsample_idx(len(dates))
    peak = np.maximum.accumulate(equity)
    drawdown = (equity / peak - 1) * 100

    def pts(arr, nd=0):
        return [round(float(v), nd) for v in np.asarray(arr)[idx]]

    curve = {
        "dates": [d.strftime("%Y-%m-%d") for d in dates[idx]],
        "strategy": pts(equity),
        "buy_hold": pts(bh),
        "drawdown": pts(drawdown, 2),
    }
    if bench_curve is not None:
        curve["benchmark"] = pts(bench_curve)

    # 價格圖（收盤價＋買賣點），同樣抽樣
    price = {
        "dates": curve["dates"],
        "close": [round(float(v), 2) for v in close[idx]],
    }

    return {
        "period": {
            "start": dates[0].strftime("%Y-%m-%d"),
            "end": dates[-1].strftime("%Y-%m-%d"),
            "days": int(len(dates)),
        },
        "stats": stats,
        "benchmark_label": benchmark_label if bench_curve is not None else None,
        "curve": curve,
        "price": price,
        "trades": sim["trades"],
        "open_position": sim["open_position"],
        "missed_limit_up": sim["missed_limit_up"],
        "yearly": yearly_returns(series, dates),
        "description": describe_strategy(strategy),
    }
