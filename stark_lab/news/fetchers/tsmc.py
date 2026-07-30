"""台積電個股新聞（中文，含摘要）→ tsmc payload（自 fetch_tsmc_news.py 移植）。"""
from __future__ import annotations

from .common import now_iso
from .news_common import cnyes, enrich, fetch, gnews


def build() -> dict:
    sources = [
        ("鉅亨網", cnyes("tw_stock")),
        ("鉅亨網", cnyes("headline")),
        ("Google 新聞", gnews("台積電 OR TSMC OR 2330 when:2d")),
    ]
    items = fetch(sources, keyword=r"台積電|TSMC|2330", max_per=60)
    if not items:
        raise RuntimeError("no tsmc news")

    items.sort(key=lambda x: (1 if x["summary"] else 0, x["_ts"]), reverse=True)
    cands = items[:8]
    enrich(cands)
    cands.sort(key=lambda x: (1 if x["summary"] else 0, x["_ts"]), reverse=True)
    top = cands[:5]

    out = [
        {
            "rank": i,
            "title": e["title"],
            "summary": e["summary"],
            "source": e["source"],
            "url": e["url"],
            "time": e["time"],
        }
        for i, e in enumerate(top, start=1)
    ]
    return {"updated_at": now_iso(), "symbol": "2330.TW", "name": "台積電", "items": out}
