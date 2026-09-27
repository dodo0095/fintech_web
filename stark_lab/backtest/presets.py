"""策略範本：給新手一鍵套用，也當作規則積木的示範。"""
from __future__ import annotations


def _ind(name, **params):
    return {"kind": "ind", "name": name, "params": params}


def _num(v):
    return {"kind": "num", "value": v}


def _c(left, op, right):
    return {"left": left, "op": op, "right": right}


PRESETS = [
    {
        "id": "ma_cross",
        "name": "均線黃金交叉",
        "desc": "5 日線向上穿越 20 日線買進，跌破就賣；搭配 10% 停損。",
        "strategy": {
            "entry": {"logic": "all", "conditions": [_c(_ind("sma", period=5), "cross_up", _ind("sma", period=20))]},
            "exit": {"logic": "any", "conditions": [_c(_ind("sma", period=5), "cross_down", _ind("sma", period=20))]},
            "risk": {"stop_loss": 10},
        },
    },
    {
        "id": "breakout",
        "name": "突破 20 日新高＋量增",
        "desc": "收盤創 20 日新高且成交量大於 5 日均量 1.5 倍；10% 移動停利、跌破月線出場。",
        "strategy": {
            "entry": {"logic": "all", "conditions": [
                _c(_ind("close"), "gt", _ind("prior_high", period=20)),
                _c(_ind("volume"), "gt", dict(_ind("vol_sma", period=5), mult=1.5)),
            ]},
            "exit": {"logic": "any", "conditions": [_c(_ind("close"), "lt", _ind("sma", period=20))]},
            "risk": {"stop_loss": 8, "trailing_stop": 10},
        },
    },
    {
        "id": "rsi_rebound",
        "name": "RSI 超賣反彈",
        "desc": "RSI(14) 由下往上穿越 30 買進，RSI 高於 70 賣出；8% 停損。",
        "strategy": {
            "entry": {"logic": "all", "conditions": [_c(_ind("rsi", period=14), "cross_up", _num(30))]},
            "exit": {"logic": "any", "conditions": [_c(_ind("rsi", period=14), "gt", _num(70))]},
            "risk": {"stop_loss": 8},
        },
    },
    {
        "id": "macd",
        "name": "MACD 翻多",
        "desc": "DIF 向上穿越訊號線且站上月線買進，DIF 跌破訊號線賣出。",
        "strategy": {
            "entry": {"logic": "all", "conditions": [
                _c(_ind("macd_dif", fast=12, slow=26, signal=9), "cross_up", _ind("macd_signal", fast=12, slow=26, signal=9)),
                _c(_ind("close"), "gt", _ind("sma", period=20)),
            ]},
            "exit": {"logic": "any", "conditions": [
                _c(_ind("macd_dif", fast=12, slow=26, signal=9), "cross_down", _ind("macd_signal", fast=12, slow=26, signal=9)),
            ]},
            "risk": {"stop_loss": 10},
        },
    },
    {
        "id": "kd_low",
        "name": "KD 低檔黃金交叉",
        "desc": "K 值在 30 以下向上穿越 D 值買進，K 向下穿越 D 賣出。",
        "strategy": {
            "entry": {"logic": "all", "conditions": [
                _c(_ind("k", period=9), "cross_up", _ind("d", period=9)),
                _c(_ind("k", period=9), "lt", _num(30)),
            ]},
            "exit": {"logic": "any", "conditions": [_c(_ind("k", period=9), "cross_down", _ind("d", period=9))]},
            "risk": {"stop_loss": 8},
        },
    },
    {
        "id": "bb_rebound",
        "name": "布林下軌反彈",
        "desc": "收盤由下往上穿越布林下軌買進，碰到上軌賣出；最多持有 20 天。",
        "strategy": {
            "entry": {"logic": "all", "conditions": [_c(_ind("close"), "cross_up", _ind("bb_lower", period=20, k=2))]},
            "exit": {"logic": "any", "conditions": [_c(_ind("close"), "ge", _ind("bb_upper", period=20, k=2))]},
            "risk": {"stop_loss": 8, "max_hold_days": 20},
        },
    },
]
