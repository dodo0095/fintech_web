"""抓取共用 helper（自 news_platform/scripts/common.py 移植，去除檔案寫入相依）。"""
from __future__ import annotations

import math
from datetime import datetime, timezone, timedelta
from typing import Any, List, Optional

TW = timezone(timedelta(hours=8))


def now_iso() -> str:
    return datetime.now(TW).replace(microsecond=0).isoformat()


def safe_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def ma(values: List[Optional[float]], window: int) -> List[Optional[float]]:
    out: List[Optional[float]] = []
    for i in range(len(values)):
        if i + 1 < window:
            out.append(None)
            continue
        chunk = values[i + 1 - window: i + 1]
        if any(x is None for x in chunk):
            out.append(None)
            continue
        out.append(round(sum(chunk) / window, 4))
    return out
