"""台積電個股新聞 → 轉呼叫泛用 stock fetcher（排程預設 2330）。"""
from __future__ import annotations

from . import stock as f_stock


def build() -> dict:
    return f_stock.build("2330")
