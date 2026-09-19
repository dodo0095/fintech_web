import datetime as dt
import math

import pandas as pd

from notify import constants as C
from notify.indicators import _crossed_above, _crossed_below, compute_adx, evaluate


def _df_from_close(close_values):
    idx = pd.date_range(end=dt.date.today(), periods=len(close_values))
    close = pd.Series([float(v) for v in close_values], index=idx)
    return pd.DataFrame(
        {"open": close, "high": close + 1, "low": close - 1, "close": close, "volume": 0},
        index=idx,
    )


def _ranging_series(length=63):
    """區間震盪（無趨勢）：正弦波，ADX 低。length=63 時同時觸發 ema(交叉型)＋bias(均值回歸)。"""
    return [100 + 6 * math.sin(i * 2 * math.pi / 10) for i in range(length)]


TREND = C.TREND_INDICATORS
MEAN_REVERSION = {"rsi", "bias", "bollinger"}


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


# --- ADX(14) 計算：趨勢高、盤整低 ---
def test_adx_high_on_trend():
    """單邊趨勢（嚴格遞增）→ ADX 高（遠超盤整閾值 25）。"""
    df = _df_from_close(range(120, 200))
    adx = compute_adx(df)
    assert adx is not None
    assert adx > C.ADX_RANGING_THRESHOLD


def test_adx_low_on_ranging():
    """區間震盪（正弦波、無趨勢）→ ADX 低（低於盤整閾值 25）。"""
    df = _df_from_close(_ranging_series(80))
    adx = compute_adx(df)
    assert adx is not None
    assert adx < C.ADX_RANGING_THRESHOLD


def test_adx_none_when_insufficient_data():
    """資料不足（< period+1）→ 回 None，安全降級。"""
    df = _df_from_close([100, 101, 102])
    assert compute_adx(df, period=14) is None


def test_adx_none_on_perfectly_flat_no_range():
    """完全無波動（high=low=close 恆定）→ ATR/DI 皆 0，安全降級為 None（不誤判）。"""
    idx = pd.date_range(end=dt.date.today(), periods=40)
    flat = pd.Series([100.0] * 40, index=idx)
    df = pd.DataFrame(
        {"open": flat, "high": flat, "low": flat, "close": flat, "volume": 0}, index=idx
    )
    assert compute_adx(df) is None


# --- A. 盤整過濾：盤整時壓制交叉型、保留均值回歸型 ---
def test_ranging_filter_suppresses_trend_keeps_mean_reversion():
    """盤整資料 + 人為交叉：交叉型（ema）被過濾、均值回歸型（bias）保留。"""
    df = _df_from_close(_ranging_series(63))
    # 確認此段確為盤整（ADX < 閾值）
    assert compute_adx(df) < C.ADX_RANGING_THRESHOLD

    base = {(s.indicator, s.direction) for s in evaluate(df, ranging_filter=False)}
    # 未過濾時：交叉型與均值回歸型皆存在（否則無法證明過濾生效）
    assert any(i in TREND for i, _ in base)
    assert any(i in MEAN_REVERSION for i, _ in base)

    filtered = {(s.indicator, s.direction) for s in evaluate(df, ranging_filter=True)}
    # 過濾後：交叉型全數消失、均值回歸型保留
    assert not any(i in TREND for i, _ in filtered)
    assert {(i, d) for i, d in base if i in MEAN_REVERSION} <= filtered


def test_trend_data_keeps_cross_signals_under_filter():
    """趨勢資料（ADX 高）：即使開啟過濾，交叉型訊號照常出現。"""
    df = _df_from_close([100] * 40 + [130])  # 平盤後急漲，末根多條交叉型觸發
    assert compute_adx(df) >= C.ADX_RANGING_THRESHOLD
    filtered = {(s.indicator, s.direction) for s in evaluate(df, ranging_filter=True)}
    assert ("ma", "bullish") in filtered
    assert ("ema", "bullish") in filtered


def test_ranging_filter_disabled_keeps_everything():
    """關閉過濾（ranging_filter=False）：盤整資料的交叉型訊號不被移除。"""
    df = _df_from_close(_ranging_series(63))
    sigs = {(s.indicator, s.direction) for s in evaluate(df, ranging_filter=False)}
    assert any(i in TREND for i, _ in sigs)
