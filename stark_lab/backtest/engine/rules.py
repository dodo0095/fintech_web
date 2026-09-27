"""策略規則：JSON schema 定義、嚴格驗證、轉成布林訊號。

使用者不寫程式；策略是一份 JSON，只能引用白名單內的指標與運算子。
驗證失敗一律丟 StrategyError（訊息為中文，可直接顯示給使用者）。

策略 JSON 結構：
{
  "entry": {"logic": "all"|"any", "conditions": [Condition, ...]},   # 至少 1 條
  "exit":  {"logic": "all"|"any", "conditions": [Condition, ...]},   # 可為空（只靠風控出場）
  "risk":  {"stop_loss": 8, "take_profit": 20, "trailing_stop": null, "max_hold_days": null}
}
Condition = {"left": Operand, "op": "gt|lt|ge|le|cross_up|cross_down", "right": Operand}
Operand   = {"kind": "ind", "name": "sma", "params": {"period": 20}, "mult": 1}
          | {"kind": "num", "value": 70}
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import indicators as ind


class StrategyError(ValueError):
    """策略內容不合法（訊息可直接給使用者看）。"""


def _p(key, label, default, lo, hi, step=1):
    return {"key": key, "label": label, "default": default, "min": lo, "max": hi, "step": step}


_PERIOD = lambda d: _p("period", "天數", d, 1, 250)  # noqa: E731
_MACD_PARAMS = [_p("fast", "快線", 12, 2, 100), _p("slow", "慢線", 26, 3, 200), _p("signal", "訊號", 9, 2, 100)]
_BB_PARAMS = [_p("period", "天數", 20, 2, 250), _p("k", "標準差倍數", 2, 0.5, 5, 0.1)]

# 指標白名單：前端下拉選單與後端驗證共用同一份定義。
# unit：同 unit 的兩個指標才適合互相比較（前端用來提示，後端不強制）。
INDICATORS: dict[str, dict] = {
    "close": {"label": "收盤價", "group": "價格", "unit": "price", "params": []},
    "open": {"label": "開盤價", "group": "價格", "unit": "price", "params": []},
    "high": {"label": "最高價", "group": "價格", "unit": "price", "params": []},
    "low": {"label": "最低價", "group": "價格", "unit": "price", "params": []},
    "sma": {"label": "均線 SMA", "group": "均線", "unit": "price", "params": [_PERIOD(20)]},
    "ema": {"label": "指數均線 EMA", "group": "均線", "unit": "price", "params": [_PERIOD(20)]},
    "prior_high": {"label": "前 N 日最高價", "group": "價格", "unit": "price", "params": [_PERIOD(20)]},
    "prior_low": {"label": "前 N 日最低價", "group": "價格", "unit": "price", "params": [_PERIOD(20)]},
    "bb_upper": {"label": "布林上軌", "group": "布林通道", "unit": "price", "params": _BB_PARAMS},
    "bb_mid": {"label": "布林中軌", "group": "布林通道", "unit": "price", "params": _BB_PARAMS},
    "bb_lower": {"label": "布林下軌", "group": "布林通道", "unit": "price", "params": _BB_PARAMS},
    "volume": {"label": "成交量（張）", "group": "成交量", "unit": "volume", "params": []},
    "vol_sma": {"label": "均量（張）", "group": "成交量", "unit": "volume", "params": [_PERIOD(5)]},
    "rsi": {"label": "RSI", "group": "擺盪指標", "unit": "0-100", "params": [_PERIOD(14)]},
    "k": {"label": "KD 的 K 值", "group": "擺盪指標", "unit": "0-100", "params": [_PERIOD(9)]},
    "d": {"label": "KD 的 D 值", "group": "擺盪指標", "unit": "0-100", "params": [_PERIOD(9)]},
    "macd_dif": {"label": "MACD 快線 DIF", "group": "MACD", "unit": "macd", "params": _MACD_PARAMS},
    "macd_signal": {"label": "MACD 訊號線", "group": "MACD", "unit": "macd", "params": _MACD_PARAMS},
    "macd_hist": {"label": "MACD 柱狀體", "group": "MACD", "unit": "macd", "params": _MACD_PARAMS},
    "roc": {"label": "N 日漲跌幅（%）", "group": "動能", "unit": "pct", "params": [_PERIOD(5)]},
}

OPERATORS: dict[str, str] = {
    "gt": "大於",
    "lt": "小於",
    "ge": "大於等於",
    "le": "小於等於",
    "cross_up": "向上穿越",
    "cross_down": "向下跌破",
}

MAX_CONDITIONS = 8
MAX_LOOKBACK = 250  # 任一指標參數上限；也決定需要多少暖機資料

RISK_FIELDS = {
    # key: (label, min, max)
    "stop_loss": ("停損 %", 0.5, 90),
    "take_profit": ("停利 %", 0.5, 1000),
    "trailing_stop": ("移動停利 %（從持有期間最高收盤回落）", 0.5, 90),
    "max_hold_days": ("最長持有天數（交易日）", 1, 2000),
}


# ---------------------------------------------------------------- 驗證

def _num(v, what: str) -> float:
    if isinstance(v, bool) or v is None:
        raise StrategyError(f"{what} 需要是數字")
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise StrategyError(f"{what} 需要是數字") from None
    if not math.isfinite(f):
        raise StrategyError(f"{what} 需要是有限數字")
    return f


def _clean_operand(op, where: str) -> dict:
    if not isinstance(op, dict):
        raise StrategyError(f"{where} 格式錯誤")
    kind = op.get("kind")
    if kind == "num":
        return {"kind": "num", "value": _num(op.get("value"), f"{where} 的數值")}
    if kind != "ind":
        raise StrategyError(f"{where} 種類不明")
    name = op.get("name")
    if name not in INDICATORS:
        raise StrategyError(f"{where} 使用了不支援的指標：{name}")
    spec = INDICATORS[name]
    raw_params = op.get("params") or {}
    if not isinstance(raw_params, dict):
        raise StrategyError(f"{where} 的參數格式錯誤")
    params = {}
    for p in spec["params"]:
        v = raw_params.get(p["key"], p["default"])
        v = _num(v, f"{where}「{spec['label']}」的{p['label']}")
        if not (p["min"] <= v <= p["max"]):
            raise StrategyError(
                f"{where}「{spec['label']}」的{p['label']}需介於 {p['min']}～{p['max']}"
            )
        params[p["key"]] = v if isinstance(p["step"], float) else int(round(v))
    if name.startswith("macd_") and params["fast"] >= params["slow"]:
        raise StrategyError(f"{where} MACD 快線天數必須小於慢線")
    mult = _num(op.get("mult", 1), f"{where} 的倍數")
    if not (0.01 <= mult <= 100):
        raise StrategyError(f"{where} 的倍數需介於 0.01～100")
    return {"kind": "ind", "name": name, "params": params, "mult": mult}


def _clean_block(block, label: str, allow_empty: bool) -> dict:
    if block is None and allow_empty:
        return {"logic": "all", "conditions": []}
    if not isinstance(block, dict):
        raise StrategyError(f"{label}條件格式錯誤")
    logic = block.get("logic", "all")
    if logic not in ("all", "any"):
        raise StrategyError(f"{label}條件的邏輯只能是「全部符合」或「任一符合」")
    conds = block.get("conditions") or []
    if not isinstance(conds, list):
        raise StrategyError(f"{label}條件格式錯誤")
    if not conds and not allow_empty:
        raise StrategyError(f"至少要有一條{label}條件")
    if len(conds) > MAX_CONDITIONS:
        raise StrategyError(f"{label}條件最多 {MAX_CONDITIONS} 條")
    out = []
    for i, c in enumerate(conds, 1):
        where = f"{label}第 {i} 條"
        if not isinstance(c, dict):
            raise StrategyError(f"{where}格式錯誤")
        if c.get("op") not in OPERATORS:
            raise StrategyError(f"{where}的比較方式不支援")
        left = _clean_operand(c.get("left"), f"{where}左邊")
        right = _clean_operand(c.get("right"), f"{where}右邊")
        if left["kind"] == "num":
            raise StrategyError(f"{where}左邊必須是指標")
        out.append({"left": left, "op": c["op"], "right": right})
    return {"logic": logic, "conditions": out}


def validate_strategy(raw) -> dict:
    """驗證並正規化策略 JSON；回傳乾淨的新 dict（不會原樣信任輸入）。"""
    if not isinstance(raw, dict):
        raise StrategyError("策略格式錯誤")
    entry = _clean_block(raw.get("entry"), "進場", allow_empty=False)
    exit_ = _clean_block(raw.get("exit"), "出場", allow_empty=True)
    risk_raw = raw.get("risk") or {}
    if not isinstance(risk_raw, dict):
        raise StrategyError("風控設定格式錯誤")
    risk = {}
    for key, (label, lo, hi) in RISK_FIELDS.items():
        v = risk_raw.get(key)
        if v in (None, "", 0, False):
            risk[key] = None
            continue
        v = _num(v, label)
        if not (lo <= v <= hi):
            raise StrategyError(f"{label}需介於 {lo}～{hi}")
        risk[key] = int(round(v)) if key == "max_hold_days" else v
    if not exit_["conditions"] and not any(risk.values()):
        raise StrategyError("請至少設定一種出場方式（出場條件、停損、停利、移動停利或最長持有天數）")
    return {"entry": entry, "exit": exit_, "risk": risk}


# ---------------------------------------------------------------- 計算

class _Calc:
    """帶快取的指標計算器（同一指標＋參數只算一次）。"""

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self._cache: dict = {}

    def series(self, name: str, params: dict) -> pd.Series:
        key = (name, tuple(sorted(params.items())))
        if key not in self._cache:
            self._cache[key] = self._compute(name, params)
        return self._cache[key]

    def _compute(self, name: str, p: dict) -> pd.Series:
        d = self.df
        if name in ("close", "open", "high", "low"):
            return d[name]
        if name == "volume":
            return d["volume"] / 1000.0  # 股 → 張
        if name == "vol_sma":
            return ind.sma(d["volume"] / 1000.0, p["period"])
        if name == "sma":
            return ind.sma(d["close"], p["period"])
        if name == "ema":
            return ind.ema(d["close"], p["period"])
        if name == "prior_high":
            return ind.prior_high(d["high"], p["period"])
        if name == "prior_low":
            return ind.prior_low(d["low"], p["period"])
        if name in ("bb_upper", "bb_mid", "bb_lower"):
            up, mid, lo = ind.bollinger(d["close"], p["period"], p["k"])
            return {"bb_upper": up, "bb_mid": mid, "bb_lower": lo}[name]
        if name == "rsi":
            return ind.rsi(d["close"], p["period"])
        if name in ("k", "d"):
            k, dd = ind.kd(d["high"], d["low"], d["close"], p["period"])
            return k if name == "k" else dd
        if name.startswith("macd_"):
            dif, dea, hist = ind.macd(d["close"], p["fast"], p["slow"], p["signal"])
            return {"macd_dif": dif, "macd_signal": dea, "macd_hist": hist}[name]
        if name == "roc":
            return ind.roc(d["close"], p["period"])
        raise StrategyError(f"不支援的指標：{name}")  # 驗證後不應發生

    def operand(self, op: dict) -> pd.Series:
        if op["kind"] == "num":
            return pd.Series(op["value"], index=self.df.index, dtype=float)
        return self.series(op["name"], op["params"]) * op.get("mult", 1)


def _condition(calc: _Calc, c: dict) -> pd.Series:
    left = calc.operand(c["left"])
    right = calc.operand(c["right"])
    valid = left.notna() & right.notna()
    op = c["op"]
    if op == "gt":
        res = left > right
    elif op == "lt":
        res = left < right
    elif op == "ge":
        res = left >= right
    elif op == "le":
        res = left <= right
    else:
        pl, pr = left.shift(1), right.shift(1)
        valid = valid & pl.notna() & pr.notna()
        if op == "cross_up":
            res = (left > right) & (pl <= pr)
        else:
            res = (left < right) & (pl >= pr)
    return (res & valid).fillna(False).astype(bool)


def _block(calc: _Calc, block: dict, empty_value: bool) -> pd.Series:
    conds = block["conditions"]
    if not conds:
        return pd.Series(empty_value, index=calc.df.index, dtype=bool)
    parts = [_condition(calc, c) for c in conds]
    arr = np.vstack([p.to_numpy() for p in parts])
    res = arr.all(axis=0) if block["logic"] == "all" else arr.any(axis=0)
    return pd.Series(res, index=calc.df.index, dtype=bool)


def build_signals(df: pd.DataFrame, strategy: dict):
    """回傳 (entry_signal, exit_signal) 布林 Series；strategy 需先經 validate_strategy。"""
    calc = _Calc(df)
    entry = _block(calc, strategy["entry"], empty_value=False)
    exit_ = _block(calc, strategy["exit"], empty_value=False)
    return entry, exit_


def warmup_days(strategy: dict) -> int:
    """估計指標需要的暖機交易日數（用來往前多抓資料）。"""
    need = 1
    for block in (strategy["entry"], strategy["exit"]):
        for c in block["conditions"]:
            for op in (c["left"], c["right"]):
                if op["kind"] != "ind":
                    continue
                p = op["params"]
                need = max(need, int(p.get("period", 1)), int(p.get("slow", 0)) + int(p.get("signal", 0)))
    # EMA/RSI/KD 類遞迴指標需要更長暖機才會收斂
    return min(need * 3 + 5, MAX_LOOKBACK * 3)


def describe_strategy(strategy: dict) -> list[str]:
    """把策略轉成人看得懂的中文句子（結果頁顯示用）。"""

    def od(o):
        if o["kind"] == "num":
            v = o["value"]
            return f"{v:g}"
        spec = INDICATORS[o["name"]]
        ps = [f"{o['params'][p['key']]:g}" for p in spec["params"]]
        s = spec["label"] + (f"({','.join(ps)})" if ps else "")
        if o.get("mult", 1) != 1:
            s += f" × {o['mult']:g}"
        return s

    lines = []
    for title, block in (("進場", strategy["entry"]), ("出場", strategy["exit"])):
        if not block["conditions"]:
            continue
        joiner = "且" if block["logic"] == "all" else "或"
        parts = [f"{od(c['left'])} {OPERATORS[c['op']]} {od(c['right'])}" for c in block["conditions"]]
        lines.append(f"{title}：" + f" {joiner} ".join(parts))
    r = strategy["risk"]
    extra = []
    if r.get("stop_loss"):
        extra.append(f"停損 {r['stop_loss']:g}%")
    if r.get("take_profit"):
        extra.append(f"停利 {r['take_profit']:g}%")
    if r.get("trailing_stop"):
        extra.append(f"移動停利 {r['trailing_stop']:g}%")
    if r.get("max_hold_days"):
        extra.append(f"最長持有 {r['max_hold_days']} 天")
    if extra:
        lines.append("風控：" + "、".join(extra))
    return lines
