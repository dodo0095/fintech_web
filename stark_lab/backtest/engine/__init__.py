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

    cap = settings.capital
    # 買進持有（簡化版：首日開盤買、不計成本）；以本金為共同起點
    close = df["close"].to_numpy(float)[start_idx:]
    first_open = float(df["open"].iloc[start_idx]) or close[0]
    bh = cap * close / first_open

    series = {"strategy": equity, "buy_hold": bh}
    bench_curve = None
    bench_start = None
    if benchmark is not None and len(benchmark):
        # 只往後補值（ffill）；基準尚未上市的期間保持 NaN，不捏造資料
        b = benchmark.sort_index().reindex(dates).ffill().to_numpy(float)
        valid = np.flatnonzero(np.isfinite(b) & (b > 0))
        if len(valid) >= MIN_BARS:
            k0 = int(valid[0])
            bench_curve = np.full(len(b), np.nan)
            bench_curve[k0:] = cap * b[k0:] / b[k0]
            bench_start = dates[k0]
            series["benchmark"] = bench_curve

    stats = {
        "strategy": curve_stats(equity, dates, base=cap),
        "buy_hold": curve_stats(bh, dates, base=cap),
    }
    if bench_curve is not None:
        k0 = int(np.flatnonzero(np.isfinite(bench_curve))[0])
        stats["benchmark"] = curve_stats(bench_curve[k0:], dates[k0:])
    stats["strategy"].update(trade_stats(sim["trades"], sim["position"]))

    # 曲線（抽樣）＋回撤
    idx = _downsample_idx(len(dates))
    peak = np.maximum.accumulate(equity)
    drawdown = (equity / peak - 1) * 100

    def pts(arr, nd=0):
        # NaN → None（JSON 不接受 NaN；前端圖表視為空白）
        return [round(float(v), nd) if np.isfinite(v) else None for v in np.asarray(arr, float)[idx]]

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
        "no_cash": sim["no_cash"],
        "benchmark_start": bench_start.strftime("%Y-%m-%d") if bench_start is not None and bench_start > dates[0] else None,
        "yearly": yearly_returns(series, dates, base=cap),
        "description": describe_strategy(strategy),
    }
