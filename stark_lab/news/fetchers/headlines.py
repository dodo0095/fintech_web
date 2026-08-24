"""美國重大新聞前五大（中文，含摘要）→ headlines payload（自 fetch_news.py 移植）。"""
from __future__ import annotations

import re

from news.heat_v1 import annotate_items

from .common import now_iso
from .news_common import cnyes, enrich, fetch, gnews

KEYWORDS_MAJOR = re.compile(
    r"美股|台股|大盤|加權|道瓊|那斯達克|納斯達克|標普|S&P|費半|"
    r"聯準會|美聯儲|Fed|FOMC|鮑爾|升息|降息|利率|通膨|CPI|非農|就業|"
    r"台積|半導體|晶片|輝達|AI|財報|殖利率|公債|油價|關稅|經濟|GDP|"
    r"科技|巨頭|蘋果|微軟|亞馬遜|特斯拉",
    re.I,
)


def build() -> dict:
    sources = [
        ("鉅亨網", cnyes("wd_stock")),
        ("Google 新聞", gnews("(美股 OR 華爾街 OR 那斯達克 OR 道瓊 OR 標普 OR 聯準會 OR 財報) when:1d")),
    ]
    items = fetch(sources)
    items = [it for it in items if KEYWORDS_MAJOR.search("{} {}".format(it["title"], it["summary"]))]
    if not items:
        raise RuntimeError("no major news")

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
            "tags": ["美股", "重大"],
            "heat": e.get("heat", 0),
            "hits_off": e.get("hits_off") or [],
            "hits_on": e.get("hits_on") or [],
            "war": bool(e.get("war")),
        }
        for i, e in enumerate(top, start=1)
    ]
    return {"updated_at": now_iso(), "items": out}
