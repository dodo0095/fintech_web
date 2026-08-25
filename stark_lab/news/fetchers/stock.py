"""任意台股個股新聞 → payload（泛化原 tsmc fetcher）。"""
from __future__ import annotations

import re

from news.heat_v1 import annotate_items
from news.tickers import default_focus, lookup
from .common import now_iso
from .news_common import cnyes, enrich, fetch, gnews


def build(code=None, name=None, yahoo=None) -> dict:
    if not code:
        info = default_focus()
    else:
        info = lookup(str(code))
        if not info:
            raise RuntimeError("unknown stock: {}".format(code))
    code = info["code"]
    name = name or info["name"]
    yahoo = yahoo or info["yahoo"]

    kw_parts = [re.escape(name), re.escape(code)]
    if code == "2330":
        kw_parts.append("TSMC")
    keyword = "|".join(kw_parts)
    if code == "2330":
        gq = "台積電 OR TSMC OR 2330 when:2d"
    else:
        gq = "{} OR {} when:2d".format(name, code)

    sources = [
        ("鉅亨網", cnyes("tw_stock")),
        ("鉅亨網", cnyes("headline")),
        ("Google 新聞", gnews(gq)),
    ]
    items = fetch(sources, keyword=keyword, max_per=60)
    if not items:
        raise RuntimeError("no stock news for {}".format(code))

    items.sort(key=lambda x: (1 if x["summary"] else 0, x["_ts"]), reverse=True)
    cands = items[:8]
    enrich(cands)
    cands.sort(key=lambda x: (1 if x["summary"] else 0, x["_ts"]), reverse=True)
    top = cands[:5]
    annotate_items(top, name, yahoo)

    out = []
    for i, e in enumerate(top, start=1):
        row = {
            "rank": i,
            "title": e["title"],
            "summary": e["summary"],
            "source": e["source"],
            "url": e["url"],
            "time": e["time"],
            "heat": e.get("heat", 0),
            "hits_off": e.get("hits_off") or [],
            "hits_on": e.get("hits_on") or [],
            "war": bool(e.get("war")),
            "name_lock": bool(e.get("name_lock")),
        }
        out.append(row)
    return {
        "updated_at": now_iso(),
        "symbol": yahoo,
        "name": name,
        "code": code,
        "items": out,
    }
