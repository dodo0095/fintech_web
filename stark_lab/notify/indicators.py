"""指標引擎 — 5 指標計算與多空觸發判定（feature-spec §2、api-design §3）。

各指標獨立判定、不做綜合。交叉類以最近兩根 K 線判定（前根未成立、當根成立），
避免持續狀態重複觸發。防抖動（24h 去重）由呼叫端依 signal_log 處理。
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import constants as C


@dataclass
class Signal:
    indicator: str
    direction: str
    detail: str


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _valid_tail(*series: pd.Series) -> bool:
    """最近兩根值皆非 NaN 才可判定。"""
    for s in series:
        if len(s) < 2 or pd.isna(s.iloc[-1]) or pd.isna(s.iloc[-2]):
            return False
    return True


def _crossed_above(a: pd.Series, b: pd.Series) -> bool:
    return bool(a.iloc[-2] <= b.iloc[-2] and a.iloc[-1] > b.iloc[-1])


def _crossed_below(a: pd.Series, b: pd.Series) -> bool:
    return bool(a.iloc[-2] >= b.iloc[-2] and a.iloc[-1] < b.iloc[-1])


def compute_adx(df: pd.DataFrame, period: int = C.ADX_PERIOD) -> float | None:
    """Wilder 標準 ADX，回傳最後一根值；資料不足或無法計算回 None（安全降級）。

    - TR = max(high-low, |high-prev_close|, |low-prev_close|)
    - +DM/-DM 標準定義；以 Wilder 平滑（EMA alpha=1/period, adjust=False）得 ATR、+DI、-DI
    - DX = 100 * |(+DI)-(-DI)| / ((+DI)+(-DI))；ADX = Wilder 平滑(DX)
    盤整（無趨勢）時 ADX 低、單邊趨勢時 ADX 高。
    """
    high = df["high"]
    low = df["low"]
    close = df["close"]
    # 至少要能算出一根 TR（需前一根收盤）；過短直接安全降級。
    if len(df) < period + 1:
        return None

    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)

    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

    alpha = 1.0 / period
    atr = tr.ewm(alpha=alpha, adjust=False).mean()
    atr_safe = atr.replace(0, np.nan)  # ATR=0（完全無波動）→ 除零保護
    plus_di = 100 * plus_dm.ewm(alpha=alpha, adjust=False).mean() / atr_safe
    minus_di = 100 * minus_dm.ewm(alpha=alpha, adjust=False).mean() / atr_safe

    di_sum = (plus_di + minus_di).replace(0, np.nan)  # +DI 與 -DI 皆 0 → 除零保護
    dx = 100 * (plus_di - minus_di).abs() / di_sum
    adx = dx.ewm(alpha=alpha, adjust=False).mean()

    val = adx.iloc[-1]
    if pd.isna(val):
        return None
    return float(val)


def evaluate(
    df: pd.DataFrame,
    ranging_filter: bool = True,
    adx_threshold: float = C.ADX_RANGING_THRESHOLD,
) -> list[Signal]:
    """回傳本次觸發的訊號列表。

    盤整過濾（A）：當 `ranging_filter=True` 且可算出 ADX 且 ADX < `adx_threshold`（盤整、
    無趨勢）時，壓制交叉/趨勢型指標（C.TREND_INDICATORS：ma/ema/macd/kd/tower），
    保留均值回歸型（rsi/bias/bollinger）。ADX 無法計算（資料不足）時不啟用過濾、回傳全部。

    本函式不依賴 Django settings，可獨立測試；開關/閾值由呼叫端（runner）自 settings 傳入。
    """
    close = df["close"]
    high = df["high"]
    low = df["low"]
    signals: list[Signal] = []

    # --- MA 均線：MA5 / MA20 交叉 ---
    ma_fast = close.rolling(C.MA_FAST).mean()
    ma_slow = close.rolling(C.MA_SLOW).mean()
    if _valid_tail(ma_fast, ma_slow):
        if _crossed_above(ma_fast, ma_slow):
            signals.append(Signal("ma", C.BULLISH, f"MA5={ma_fast.iloc[-1]:.2f} 上穿 MA20={ma_slow.iloc[-1]:.2f}"))
        elif _crossed_below(ma_fast, ma_slow):
            signals.append(Signal("ma", C.BEARISH, f"MA5={ma_fast.iloc[-1]:.2f} 下穿 MA20={ma_slow.iloc[-1]:.2f}"))

    # --- MACD：柱狀圖轉正/轉負（等同 MACD 線穿越訊號線）---
    macd_line = _ema(close, C.MACD_FAST) - _ema(close, C.MACD_SLOW)
    signal_line = _ema(macd_line, C.MACD_SIGNAL)
    hist = macd_line - signal_line
    if _valid_tail(hist):
        if hist.iloc[-2] <= 0 < hist.iloc[-1]:
            signals.append(Signal("macd", C.BULLISH, f"柱狀圖轉正 {hist.iloc[-1]:.3f}"))
        elif hist.iloc[-2] >= 0 > hist.iloc[-1]:
            signals.append(Signal("macd", C.BEARISH, f"柱狀圖轉負 {hist.iloc[-1]:.3f}"))

    # --- RSI(14)：超賣/超買（水準條件）---
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / C.RSI_PERIOD, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / C.RSI_PERIOD, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    # avg_loss=0 且有漲幅 → RSI=100（純漲，超買）；avg_loss=avg_gain=0（平盤）→ 留 NaN 不觸發
    rsi = rsi.mask((avg_loss == 0) & (avg_gain > 0), 100.0)
    if _valid_tail(rsi):
        val = rsi.iloc[-1]
        if val < C.RSI_OVERSOLD:
            signals.append(Signal("rsi", C.BULLISH, f"RSI={val:.1f}（超賣<{C.RSI_OVERSOLD}）"))
        elif val > C.RSI_OVERBOUGHT:
            signals.append(Signal("rsi", C.BEARISH, f"RSI={val:.1f}（超買>{C.RSI_OVERBOUGHT}）"))

    # --- KD(9,3,3)：低檔黃金交叉 / 高檔死亡交叉 ---
    low_min = low.rolling(C.KD_PERIOD).min()
    high_max = high.rolling(C.KD_PERIOD).max()
    rng = (high_max - low_min).replace(0, np.nan)
    rsv = (close - low_min) / rng * 100
    k = rsv.rolling(C.KD_SMOOTH_K).mean()
    d = k.rolling(C.KD_SMOOTH_D).mean()
    if _valid_tail(k, d):
        if _crossed_above(k, d) and k.iloc[-1] < C.KD_LOW:
            signals.append(Signal("kd", C.BULLISH, f"K={k.iloc[-1]:.1f} 低檔上穿 D={d.iloc[-1]:.1f}"))
        elif _crossed_below(k, d) and k.iloc[-1] > C.KD_HIGH:
            signals.append(Signal("kd", C.BEARISH, f"K={k.iloc[-1]:.1f} 高檔下穿 D={d.iloc[-1]:.1f}"))

    # --- 布林通道(20, ±2σ)：觸及上下軌（水準條件）---
    mid = close.rolling(C.BB_PERIOD).mean()
    std = close.rolling(C.BB_PERIOD).std()
    upper = mid + C.BB_STD * std
    lower = mid - C.BB_STD * std
    if _valid_tail(upper, lower) and std.iloc[-1] > 0:
        price = close.iloc[-1]
        if price <= lower.iloc[-1]:
            signals.append(Signal("bollinger", C.BULLISH, f"收盤 {price:.2f} 觸及下軌 {lower.iloc[-1]:.2f}"))
        elif price >= upper.iloc[-1]:
            signals.append(Signal("bollinger", C.BEARISH, f"收盤 {price:.2f} 觸及上軌 {upper.iloc[-1]:.2f}"))

    # --- EMA：EMA12 / EMA26 交叉 ---
    ema_fast = _ema(close, C.EMA_FAST)
    ema_slow = _ema(close, C.EMA_SLOW)
    if _valid_tail(ema_fast, ema_slow):
        if _crossed_above(ema_fast, ema_slow):
            signals.append(Signal("ema", C.BULLISH, f"EMA12={ema_fast.iloc[-1]:.2f} 上穿 EMA26={ema_slow.iloc[-1]:.2f}"))
        elif _crossed_below(ema_fast, ema_slow):
            signals.append(Signal("ema", C.BEARISH, f"EMA12={ema_fast.iloc[-1]:.2f} 下穿 EMA26={ema_slow.iloc[-1]:.2f}"))

    # --- 乖離率 BIAS：收盤對 MA_N 的百分比偏離（水準條件）---
    bias_ma = close.rolling(C.BIAS_PERIOD).mean()
    if _valid_tail(bias_ma) and bias_ma.iloc[-1] != 0:
        bias = (close.iloc[-1] - bias_ma.iloc[-1]) / bias_ma.iloc[-1] * 100
        if bias <= C.BIAS_OVERSOLD:
            signals.append(Signal("bias", C.BULLISH, f"BIAS={bias:.2f}%（超賣≤{C.BIAS_OVERSOLD}%）"))
        elif bias >= C.BIAS_OVERBOUGHT:
            signals.append(Signal("bias", C.BEARISH, f"BIAS={bias:.2f}%（超買≥{C.BIAS_OVERBOUGHT}%）"))

    # --- 寶塔線 TOWER：僅收盤價、翻紅/翻黑，只在翻色當根觸發 ---
    closes = [float(v) for v in close.tolist()]
    if len(closes) >= C.TOWER_REF + 1:
        states: list[str | None] = []
        state: str | None = None
        for i in range(C.TOWER_REF, len(closes)):
            window = closes[i - C.TOWER_REF:i]
            cur = closes[i]
            if cur > max(window):
                state = "red"
            elif cur < min(window):
                state = "black"
            states.append(state)
        if len(states) >= 2 and states[-1] is not None and states[-1] != states[-2]:
            if states[-1] == "red":
                signals.append(Signal("tower", C.BULLISH, f"翻紅 收盤 {closes[-1]:.2f}"))
            elif states[-1] == "black":
                signals.append(Signal("tower", C.BEARISH, f"翻黑 收盤 {closes[-1]:.2f}"))

    # --- A. 盤整過濾（ADX trend filter）：盤整時壓制交叉型、保留均值回歸型 ---
    if ranging_filter:
        adx = compute_adx(df, C.ADX_PERIOD)
        # ADX 可算出且低於閾值 → 盤整；ADX 為 None（資料不足）則安全降級、不過濾。
        if adx is not None and adx < adx_threshold:
            signals = [s for s in signals if s.indicator not in C.TREND_INDICATORS]

    return signals
