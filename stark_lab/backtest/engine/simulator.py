"""單一標的、只做多的逐日交易模擬。

撮合規則（避免偷看未來、盡量貼近台股實況）：
- 訊號在 T 日收盤後確認 → T+1 日開盤價成交（再加滑價）。
- 停損／停利在盤中檢查：跳空開盤穿越就以開盤價成交，否則以觸價成交；
  同一天同時碰到停損與停利時，保守假設先碰停損。
- 移動停利以「持有期間最高收盤價」回落計算，於盤中檢查。
- 一字鎖漲停（最高=最低且開盤漲幅 ≥ 9.5%）買不到；一字鎖跌停賣不掉，順延。
- 成本：手續費 0.1425% × 折扣（最低 20 元）、證交稅 股票 0.3%／ETF 0.1%（賣出時）。
- 資金全進全出；可選零股（1 股為單位）或整張（1000 股）。
- 回測結束仍持有的部位，以最後收盤價結算並標記為「未平倉」。
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

FEE_RATE = 0.001425
MIN_FEE = 20.0
TAX_STOCK = 0.003
TAX_ETF = 0.001
LIMIT_MOVE = 0.095  # 台股漲跌幅 10%，留一點浮點與還原價誤差空間


@dataclass
class Settings:
    capital: float = 1_000_000
    fee_discount: float = 0.6  # 券商手續費折扣（0.6 = 六折）
    slippage_pct: float = 0.1  # 單邊滑價 %
    board_lot: bool = False  # True = 只能買整張
    is_etf: bool = False


def _fee(amount: float, s: Settings) -> float:
    if s.fee_discount <= 0:  # 0 折 = 不計手續費（證交稅仍照收）
        return 0.0
    return max(MIN_FEE, amount * FEE_RATE * s.fee_discount)


def simulate(
    df: pd.DataFrame,
    entry_sig: pd.Series,
    exit_sig: pd.Series,
    risk: dict,
    settings: Settings,
    start_idx: int = 0,
) -> dict:
    """df 需含 open/high/low/close 欄位（DatetimeIndex、已排序）。

    start_idx 之前的資料只用於指標暖機，不交易、不計績效。
    回傳 {"equity": ndarray, "position": ndarray(0/1), "trades": [...]}（長度 = len(df) - start_idx）。
    """
    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    lo = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    dates = df.index
    ent = entry_sig.to_numpy(bool)
    ext = exit_sig.to_numpy(bool)
    n = len(df)

    sl = (risk.get("stop_loss") or 0) / 100
    tp = (risk.get("take_profit") or 0) / 100
    ts = (risk.get("trailing_stop") or 0) / 100
    max_hold = risk.get("max_hold_days") or 0
    slip = settings.slippage_pct / 100
    tax = TAX_ETF if settings.is_etf else TAX_STOCK
    lot = 1000 if settings.board_lot else 1

    cash = float(settings.capital)
    shares = 0
    entry_price = 0.0
    entry_cost = 0.0  # 含手續費的總買進成本
    entry_i = -1
    peak_close = 0.0
    trades: list[dict] = []
    missed_limit = 0

    equity = np.empty(n - start_idx)
    position = np.zeros(n - start_idx, dtype=np.int8)

    def locked_up(i):
        return i > 0 and h[i] == lo[i] and o[i] >= c[i - 1] * (1 + LIMIT_MOVE)

    def locked_down(i):
        return i > 0 and h[i] == lo[i] and o[i] <= c[i - 1] * (1 - LIMIT_MOVE)

    def sell(i, raw_price, reason):
        nonlocal cash, shares
        price = raw_price * (1 - slip)
        amount = price * shares
        proceeds = amount - _fee(amount, settings) - amount * tax
        cash += proceeds
        pnl = proceeds - entry_cost
        trades.append({
            "entry_date": dates[entry_i].strftime("%Y-%m-%d"),
            "entry_price": round(entry_price, 4),
            "exit_date": dates[i].strftime("%Y-%m-%d"),
            "exit_price": round(price, 4),
            "shares": int(shares),
            "hold_days": int(i - entry_i),
            "pnl": round(pnl, 0),
            "return_pct": round(pnl / entry_cost * 100, 2),
            "reason": reason,
        })
        shares = 0

    for i in range(start_idx, n):
        if not all(map(math.isfinite, (o[i], h[i], lo[i], c[i]))):
            # 缺值日：不交易，沿用前一天權益
            k = i - start_idx
            equity[k] = equity[k - 1] if k > 0 else cash
            position[k] = 1 if shares else 0
            continue

        # ---- 1) 開盤：處理前一日收盤確認的訊號
        if i > start_idx:
            if shares:
                reason = None
                if ext[i - 1]:
                    reason = "出場條件"
                elif max_hold and (i - 1 - entry_i) >= max_hold:
                    reason = "持有天數到期"
                if reason and not locked_down(i):
                    sell(i, o[i], reason)
            elif ent[i - 1]:
                if locked_up(i):
                    missed_limit += 1
                else:
                    price = o[i] * (1 + slip)
                    # 先扣手續費預留後計算可買股數
                    budget = cash - _fee(cash, settings)
                    qty = int(budget // price) // lot * lot if price > 0 else 0
                    if qty > 0:
                        amount = price * qty
                        cost = amount + _fee(amount, settings)
                        if cost > cash:  # 最低手續費邊界
                            qty -= lot
                            amount = price * qty
                            cost = amount + _fee(amount, settings)
                        if qty > 0:
                            cash -= cost
                            shares = qty
                            entry_price = price
                            entry_cost = cost
                            entry_i = i
                            peak_close = price

        # ---- 2) 盤中：停損／移動停利／停利
        if shares:
            stop_levels = []
            if sl:
                stop_levels.append((entry_price * (1 - sl), "停損"))
            if ts and peak_close:
                stop_levels.append((peak_close * (1 - ts), "移動停利"))
            hit = None
            if stop_levels:
                level, why = max(stop_levels, key=lambda x: x[0])  # 最先被碰到的是較高的那條
                if lo[i] <= level:
                    hit = (min(o[i], level), why)
            if hit is None and tp:
                level = entry_price * (1 + tp)
                if h[i] >= level:
                    hit = (max(o[i], level), "停利")
            if hit and not (locked_down(i) and hit[1] != "停利"):
                sell(i, hit[0], hit[1])

        if shares:
            peak_close = max(peak_close, c[i])

        k = i - start_idx
        equity[k] = cash + shares * c[i]
        position[k] = 1 if shares else 0

    open_position = None
    if shares:
        last = n - 1
        # 以最後收盤計算（含假設賣出成本），標示未平倉
        sell(last, c[last] / (1 - slip) if slip < 1 else c[last], "未平倉（以最後收盤計）")
        open_position = trades[-1]
        equity[-1] = cash

    return {
        "equity": equity,
        "position": position,
        "trades": trades,
        "open_position": open_position,
        "missed_limit_up": missed_limit,
    }
