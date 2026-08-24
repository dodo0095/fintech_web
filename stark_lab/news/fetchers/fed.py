"""聯準會（Fed）發言重點（中文，含摘要）→ fed payload（自 fetch_fed.py 移植）。"""
from __future__ import annotations

import re

from news.heat_v1 import annotate_items

from .common import now_iso
from .news_common import cnyes, enrich, fetch, gnews

KW_HAWK = re.compile(r"升息|加息|鷹|抗通膨|通膨|緊縮|按兵不動|維持利率|保持耐心|不急於|不降息")
KW_DOVE = re.compile(r"降息|減息|鴿|寬鬆|放緩|降溫|轉向|軟著陸|降利率")


def stance(text: str) -> str:
    h = 1 if KW_HAWK.search(text) else 0
    d = 1 if KW_DOVE.search(text) else 0
    if h and not d:
        return "hawk"
    if d and not h:
        return "dove"
    return "neutral"


def build() -> dict:
    sources = [
        ("鉅亨網", cnyes("wd_stock")),
        ("鉅亨網", cnyes("headline")),
        ("Google 新聞", gnews("(聯準會 OR Fed OR 鮑爾 OR FOMC) (利率 OR 通膨 OR 降息 OR 升息) when:3d")),
    ]
    items = fetch(sources, keyword=r"聯準會|美聯儲|Fed|FOMC|鮑爾|降息|升息|利率|通膨")
    if not items:
        raise RuntimeError("no fed news")

    items.sort(key=lambda x: (1 if x["summary"] else 0, x["_ts"]), reverse=True)
    cands = items[:8]
    enrich(cands)
    cands.sort(key=lambda x: (1 if x["summary"] else 0, x["_ts"]), reverse=True)
    top = cands[:5]

    annotate_items(top)
    out = [
        {
            "rank": i,
            "title": e["title"],
            "summary": e["summary"],
            "source": e["source"],
            "url": e["url"],
            "time": e["time"],
            "stance": stance("{} {}".format(e["title"], e["summary"])),
            "heat": e.get("heat", 0),
            "hits_off": e.get("hits_off") or [],
            "hits_on": e.get("hits_on") or [],
            "war": bool(e.get("war")),
        }
        for i, e in enumerate(top, start=1)
    ]
    return {"updated_at": now_iso(), "items": out}
