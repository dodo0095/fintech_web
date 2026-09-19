import datetime as dt

import pandas as pd

from notify.indicators import _crossed_above, _crossed_below, evaluate


def _df_from_close(close_values):
    idx = pd.date_range(end=dt.date.today(), periods=len(close_values))
    close = pd.Series([float(v) for v in close_values], index=idx)
    return pd.DataFrame(
        {"open": close, "high": close + 1, "low": close - 1, "close": close, "volume": 0},
        index=idx,
    )


def test_crossed_above():
    a = pd.Series([1, 2, 5])
    b = pd.Series([3, 3, 3])
    assert _crossed_above(a, b) is True
    assert _crossed_below(a, b) is False


def test_crossed_below():
    a = pd.Series([5, 4, 1])
    b = pd.Series([3, 3, 3])
    assert _crossed_below(a, b) is True


def test_strictly_decreasing_triggers_rsi_bullish():
    df = _df_from_close(range(200, 120, -1))  # 80 根、嚴格遞減 → RSI=0
    sigs = {(s.indicator, s.direction) for s in evaluate(df)}
    assert ("rsi", "bullish") in sigs


def test_strictly_increasing_triggers_rsi_bearish():
    df = _df_from_close(range(120, 200))  # 嚴格遞增 → RSI=100
    sigs = {(s.indicator, s.direction) for s in evaluate(df)}
    assert ("rsi", "bearish") in sigs


def test_flat_series_no_signal():
    df = _df_from_close([100] * 80)
    assert evaluate(df) == []


# --- EMA 交叉 ---
def test_ema_golden_cross_bullish():
    df = _df_from_close([100] * 40 + [130])  # 末根急漲 → EMA12 上穿 EMA26
    sigs = {(s.indicator, s.direction) for s in evaluate(df)}
    assert ("ema", "bullish") in sigs


def test_ema_death_cross_bearish():
    df = _df_from_close([100] * 40 + [70])  # 末根急跌 → EMA12 下穿 EMA26
    sigs = {(s.indicator, s.direction) for s in evaluate(df)}
    assert ("ema", "bearish") in sigs


# --- 乖離率 BIAS ---
def test_bias_oversold_bullish():
    df = _df_from_close([100] * 40 + [90])  # 收盤遠低於 MA10 → BIAS≈-9%
    sigs = {(s.indicator, s.direction) for s in evaluate(df)}
    assert ("bias", "bullish") in sigs


def test_bias_overbought_bearish():
    df = _df_from_close([100] * 40 + [110])  # 收盤遠高於 MA10 → BIAS≈+9%
    sigs = {(s.indicator, s.direction) for s in evaluate(df)}
    assert ("bias", "bearish") in sigs


# --- 寶塔線 TOWER ---
def test_tower_flip_red_bullish():
    df = _df_from_close(list(range(140, 100, -1)) + [105])  # 一路黑後末根突破前兩根 → 翻紅
    sigs = {(s.indicator, s.direction) for s in evaluate(df)}
    assert ("tower", "bullish") in sigs


def test_tower_flip_black_bearish():
    df = _df_from_close(list(range(100, 140)) + [130])  # 一路紅後末根跌破前兩根 → 翻黑
    sigs = {(s.indicator, s.direction) for s in evaluate(df)}
    assert ("tower", "bearish") in sigs


# --- MA 交叉（fixture 皆經 evaluate 實測確認）---
def test_ma_golden_cross_bullish():
    df = _df_from_close([100] * 40 + [130])  # 平盤後末根急漲 → MA5 上穿 MA20
    sigs = {(s.indicator, s.direction) for s in evaluate(df)}
    assert ("ma", "bullish") in sigs


def test_ma_death_cross_bearish():
    df = _df_from_close([100] * 40 + [70])  # 平盤後末根急跌 → MA5 下穿 MA20
    sigs = {(s.indicator, s.direction) for s in evaluate(df)}
    assert ("ma", "bearish") in sigs


# --- MACD 柱狀圖轉正/轉負 ---
def test_macd_histogram_turns_positive_bullish():
    df = _df_from_close([100] * 40 + [130])
    sigs = {(s.indicator, s.direction) for s in evaluate(df)}
    assert ("macd", "bullish") in sigs


def test_macd_histogram_turns_negative_bearish():
    df = _df_from_close([100] * 40 + [70])
    sigs = {(s.indicator, s.direction) for s in evaluate(df)}
    assert ("macd", "bearish") in sigs


# --- KD 低檔金叉 / 高檔死叉（交叉落在最後一根、K 在低/高檔）---
def test_kd_low_golden_cross_bullish():
    df = _df_from_close(list(range(160, 100, -1)) + [102])  # 一路跌到底、末根微升 → 低檔 K 上穿 D
    sigs = {(s.indicator, s.direction) for s in evaluate(df)}
    assert ("kd", "bullish") in sigs


def test_kd_high_death_cross_bearish():
    df = _df_from_close(list(range(100, 160)) + [157])  # 一路漲到頂、末根微降 → 高檔 K 下穿 D
    sigs = {(s.indicator, s.direction) for s in evaluate(df)}
    assert ("kd", "bearish") in sigs


# --- 布林通道 觸及上下軌 ---
def test_bollinger_touches_lower_band_bullish():
    df = _df_from_close([100] * 25 + [90])  # 平盤後末根跌破下軌
    sigs = {(s.indicator, s.direction) for s in evaluate(df)}
    assert ("bollinger", "bullish") in sigs


def test_bollinger_touches_upper_band_bearish():
    df = _df_from_close([100] * 25 + [110])  # 平盤後末根突破上軌
    sigs = {(s.indicator, s.direction) for s in evaluate(df)}
    assert ("bollinger", "bearish") in sigs
