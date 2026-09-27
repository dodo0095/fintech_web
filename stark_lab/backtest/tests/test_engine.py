"""回測引擎單元測試（純 pandas，不需 Django、不連網）。

執行：python -m pytest backtest/tests/test_engine.py -q
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backtest.engine import Settings, StrategyError, run_backtest, validate_strategy
from backtest.engine import indicators as ind
from backtest.engine.rules import build_signals
from backtest.engine.simulator import simulate


def make_df(closes, opens=None, highs=None, lows=None, start="2020-01-01"):
    closes = np.asarray(closes, float)
    idx = pd.bdate_range(start, periods=len(closes))
    opens = closes if opens is None else np.asarray(opens, float)
    highs = np.maximum(opens, closes) if highs is None else np.asarray(highs, float)
    lows = np.minimum(opens, closes) if lows is None else np.asarray(lows, float)
    return pd.DataFrame(
        {"open": opens, "high": highs, "low": lows, "close": closes, "volume": 1_000_000},
        index=idx,
    )


def gt_num(name, value, **params):
    return {"left": {"kind": "ind", "name": name, "params": params}, "op": "gt",
            "right": {"kind": "num", "value": value}}


NO_COST = Settings(capital=100_000, fee_discount=0, slippage_pct=0)


# ---------------------------------------------------------------- 指標

def test_sma_and_prior_high():
    s = pd.Series([1, 2, 3, 4, 5], dtype=float)
    assert ind.sma(s, 3).tolist()[2:] == [2, 3, 4]
    assert np.isnan(ind.sma(s, 3).iloc[1])
    # 前 2 日最高（不含當日）
    assert ind.prior_high(s, 2).tolist()[2:] == [2, 3, 4]


def test_rsi_bounds():
    up = pd.Series(np.arange(1, 40, dtype=float))
    assert ind.rsi(up, 14).dropna().eq(100).all()
    rnd = pd.Series(np.cumsum(np.random.default_rng(0).normal(0, 1, 300)) + 100)
    r = ind.rsi(rnd, 14).dropna()
    assert ((r >= 0) & (r <= 100)).all()


def test_kd_range():
    rng = np.random.default_rng(1)
    c = pd.Series(100 + np.cumsum(rng.normal(0, 1, 200)))
    k, d = ind.kd(c + 1, c - 1, c, 9)
    k, d = k.dropna(), d.dropna()
    assert ((k >= 0) & (k <= 100)).all() and ((d >= 0) & (d <= 100)).all()


# ---------------------------------------------------------------- 驗證

def test_validate_rejects_unknown_indicator():
    with pytest.raises(StrategyError):
        validate_strategy({"entry": {"conditions": [gt_num("__import__", 1)]},
                           "risk": {"stop_loss": 5}})


def test_validate_requires_exit_method():
    with pytest.raises(StrategyError, match="出場"):
        validate_strategy({"entry": {"conditions": [gt_num("close", 1)]}})


def test_validate_param_range_and_cast():
    s = validate_strategy({"entry": {"conditions": [gt_num("sma", 1, period="20")]},
                           "risk": {"stop_loss": "5"}})
    assert s["entry"]["conditions"][0]["left"]["params"] == {"period": 20}
    assert s["risk"]["stop_loss"] == 5.0
    with pytest.raises(StrategyError):
        validate_strategy({"entry": {"conditions": [gt_num("sma", 1, period=9999)]},
                           "risk": {"stop_loss": 5}})


def test_validate_rejects_nan_and_bool():
    for bad in (float("nan"), True, "abc", None):
        with pytest.raises(StrategyError):
            validate_strategy({"entry": {"conditions": [gt_num("close", bad)]},
                               "risk": {"stop_loss": 5}})


# ---------------------------------------------------------------- 撮合

def test_trade_executes_next_day_open_no_lookahead():
    # 第 3 天(索引2)收盤 > 10 → 第 4 天(索引3)開盤買；出場條件 close > 13 → 隔日開盤賣
    closes = [10, 10, 11, 12, 14, 15, 15]
    opens = [10, 10, 10.5, 11.5, 13, 16, 15]
    df = make_df(closes, opens)
    strat = validate_strategy({
        "entry": {"conditions": [gt_num("close", 10.5)]},
        "exit": {"conditions": [gt_num("close", 13)]},
    })
    e, x = build_signals(df, strat)
    res = simulate(df, e, x, strat["risk"], NO_COST)
    t = res["trades"][0]
    assert t["entry_date"] == df.index[3].strftime("%Y-%m-%d")
    assert t["entry_price"] == 11.5
    assert t["exit_date"] == df.index[5].strftime("%Y-%m-%d")
    assert t["exit_price"] == 16
    assert t["reason"] == "出場條件"


def test_stop_loss_intraday_and_gap():
    # 買在 100，停損 5% → 95。第二天盤中低點 94 → 以 95 出場
    df = make_df([100, 100, 100, 99, 99], opens=[100, 100, 100, 99, 99],
                 lows=[100, 100, 100, 94, 99])
    strat = validate_strategy({"entry": {"conditions": [gt_num("close", 50)]},
                               "risk": {"stop_loss": 5}})
    e, x = build_signals(df, strat)
    t = simulate(df, e, x, strat["risk"], NO_COST)["trades"][0]
    assert t["reason"] == "停損" and t["exit_price"] == 95

    # 跳空開低 90（低於 95）→ 以開盤 90 出場
    df2 = make_df([100, 100, 100, 91, 91], opens=[100, 100, 100, 90, 91],
                  lows=[100, 100, 100, 89, 91])
    e, x = build_signals(df2, strat)
    t = simulate(df2, e, x, strat["risk"], NO_COST)["trades"][0]
    assert t["exit_price"] == 90


def test_locked_limit_up_cannot_buy():
    # 訊號出現後隔天一字漲停（開=高=低=收，+10%）→ 買不到
    closes = [10, 10, 11, 11, 11]
    df = make_df(closes, opens=[10, 10, 11, 11, 11], highs=[10, 10, 11, 11, 11],
                 lows=[10, 10, 11, 11, 11])
    strat = validate_strategy({
        "entry": {"conditions": [{"left": {"kind": "ind", "name": "close"}, "op": "cross_up",
                                  "right": {"kind": "num", "value": 9.99}}]},
        "risk": {"stop_loss": 5}})
    # cross_up 在第 0 天無前值→不成立；手動構造：第 1 天訊號
    e = pd.Series([False, True, False, False, False], index=df.index)
    x = pd.Series(False, index=df.index)
    res = simulate(df, e, x, strat["risk"], NO_COST)
    assert res["trades"] == [] and res["missed_limit_up"] == 1


def test_costs_reduce_equity():
    df = make_df([100] * 30)
    strat = validate_strategy({"entry": {"conditions": [gt_num("close", 50)]},
                               "risk": {"max_hold_days": 3}})
    e, x = build_signals(df, strat)
    cost = simulate(df, e, x, strat["risk"], Settings(capital=100_000))
    free = simulate(df, e, x, strat["risk"], NO_COST)
    # 價格不動：免手續費時每筆只虧證交稅 0.3%
    assert all(t["return_pct"] == pytest.approx(-0.3, abs=0.01) for t in free["trades"])
    # 加上手續費後權益更低
    assert cost["equity"][-1] < free["equity"][-1] < 100_000


def test_board_lot_rounds_to_1000():
    df = make_df([100] * 30)
    strat = validate_strategy({"entry": {"conditions": [gt_num("close", 50)]},
                               "risk": {"max_hold_days": 5}})
    e, x = build_signals(df, strat)
    s = Settings(capital=250_000, board_lot=True)
    t = simulate(df, e, x, strat["risk"], s)["trades"][0]
    assert t["shares"] == 2000


def test_run_backtest_end_to_end():
    rng = np.random.default_rng(7)
    closes = 100 * np.exp(np.cumsum(rng.normal(0.0004, 0.02, 800)))
    df = make_df(closes)
    strat = validate_strategy({
        "entry": {"conditions": [{"left": {"kind": "ind", "name": "sma", "params": {"period": 5}},
                                  "op": "cross_up",
                                  "right": {"kind": "ind", "name": "sma", "params": {"period": 20}}}]},
        "exit": {"conditions": [{"left": {"kind": "ind", "name": "sma", "params": {"period": 5}},
                                 "op": "cross_down",
                                 "right": {"kind": "ind", "name": "sma", "params": {"period": 20}}}]},
        "risk": {"stop_loss": 10},
    })
    res = run_backtest(df, strat, Settings(), df.index[100], df.index[-1],
                       benchmark=df["close"] * 0.5)
    st = res["stats"]["strategy"]
    assert st["trades"] > 0
    assert res["period"]["start"] == df.index[100].strftime("%Y-%m-%d")
    assert len(res["curve"]["dates"]) == len(res["curve"]["strategy"])
    assert res["stats"]["benchmark"]["total_return"] == pytest.approx(
        res["stats"]["buy_hold"]["total_return"], abs=0.5)  # 基準 = 同價格縮放
    assert res["yearly"][0]["year"] == df.index[100].year
    # 交易都在回測區間內
    assert all(t["entry_date"] >= res["period"]["start"] for t in res["trades"])


def test_run_backtest_too_short_range():
    df = make_df([100] * 50)
    strat = validate_strategy({"entry": {"conditions": [gt_num("close", 50)]},
                               "risk": {"stop_loss": 5}})
    with pytest.raises(StrategyError):
        run_backtest(df, strat, Settings(), df.index[45], df.index[-1])
