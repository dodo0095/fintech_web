"""共用新聞抓取（自 news_platform/scripts/news_common.py 移植，改為套件相對匯入）。

- 鉅亨網（cnYES）分類 RSS：description 有真實內文摘要 → 取為 summary。
- Google 新聞 zh-TW：穩定、必中文，但 description 僅標題/來源 → summary 留空（僅備援補量）。
- 統一濾除「盤中速報」等個股跳動快訊、去重、可用關鍵字過濾。

回傳項目：{title, summary, source, url, time(iso), _ts}
"""
from __future__ import annotations

import re
from datetime import timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote

from .common import TW, now_iso

# 個股跳動快訊 — 一律濾除
NOISE = re.compile(
    r"盤中速報|盤後速報|速報|急拉|急殺|急跌|急漲|委買|委賣|漲停|跌停|鎖死|跳空|"
    r"成交\d+張|近\d+日股價|三大法人買賣超"
)


def gnews(query: str) -> str:
    return "https://news.google.com/rss/search?q=" + quote(query) + "&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"


def cnyes(category: str) -> str:
    return "https://news.cnyes.com/rss/v1/news/category/{}".format(category)


def _strip(t: str) -> str:
    t = re.sub(r"<[^>]+>", " ", t or "")
    return re.sub(r"\s+", " ", t).strip()


def _summarize(t: str, n: int = 90) -> str:
    t = _strip(t)
    return t if len(t) <= n else t[: n - 1].rstrip() + "…"


def _parse_time(entry):
    for k in ("published", "updated"):
        raw = entry.get(k)
        if raw:
            try:
                dt = parsedate_to_datetime(raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(TW)
            except Exception:
                pass
    return None


# 抓到這類罐頭文字視為「無摘要」
JUNK_DESC = re.compile(
    r"Comprehensive up-to-date news coverage|aggregated from sources|by Google News|"
    r"全面的最新新聞報導|Google 新聞",
    re.I,
)


def enrich(items):
    """對 summary 為空的項目，抓文章頁的 og:description / meta description 補摘要。"""
    try:
        import requests
        from bs4 import BeautifulSoup
    except Exception:
        return items

    headers = {"User-Agent": "Mozilla/5.0 (compatible; StarkLabNews/1.0)"}
    for it in items:
        url = it.get("url") or ""
        if it.get("summary") or not url:
            continue
        if "google." in url:  # Google 新聞連結拿不到原文，跳過
            continue
        try:
            r = requests.get(url, timeout=6, headers=headers, allow_redirects=True)
            if not r.ok or not r.text:
                continue
            soup = BeautifulSoup(r.text, "html.parser")
            desc = ""
            for attrs in ({"property": "og:description"}, {"name": "description"}, {"name": "twitter:description"}):
                tag = soup.find("meta", attrs=attrs)
                if tag and tag.get("content") and len(tag["content"].strip()) > 15:
                    desc = tag["content"].strip()
                    break
            if not desc:
                p = soup.find("p")
                if p:
                    txt = _strip(p.get_text())
                    if len(txt) > 20:
                        desc = txt
            if desc and not JUNK_DESC.search(desc):
                it["summary"] = _summarize(desc)
        except Exception:
            continue
    return items


def _rss_entries_stdlib(url):
    """stdlib RSS reader — production may not have feedparser installed."""
    import urllib.request
    import xml.etree.ElementTree as ET

    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (compatible; StarkLabNews/1.0)"}
    )
    with urllib.request.urlopen(req, timeout=12) as resp:
        raw = resp.read()
    root = ET.fromstring(raw)
    entries = []
    for item in root.iter("item"):
        def _text(tag):
            el = item.find(tag)
            return (el.text or "") if el is not None else ""

        entries.append({
            "title": _text("title"),
            "summary": _text("description"),
            "description": _text("description"),
            "link": _text("link"),
            "published": _text("pubDate"),
            "updated": _text("pubDate"),
        })
    return entries


def _rss_entries(url, max_per):
    try:
        import feedparser
    except ImportError:
        return _rss_entries_stdlib(url)[:max_per]
    feed = feedparser.parse(url)
    out = []
    for e in feed.entries[:max_per]:
        out.append({
            "title": e.get("title") or "",
            "summary": e.get("summary") or e.get("description") or "",
            "description": e.get("description") or "",
            "link": e.get("link") or "",
            "published": e.get("published") or e.get("updated") or "",
            "updated": e.get("updated") or e.get("published") or "",
        })
    return out


def fetch(sources, keyword=None, max_per: int = 50):
    """sources: list[(name, url)]。cnYES 來源取真實摘要，Google 僅標題。

    keyword: 需符合的正規式（比對 title+summary），None 不過濾。
    回傳去重、濾噪音後的 list（未截斷數量，呼叫端自行排序取前 N）。
    feedparser 沒裝時改走標準庫 RSS。
    """
    kw = re.compile(keyword) if keyword else None
    seen = set()
    out = []

    for name, url in sources:
        has_summary = "cnyes" in url
        try:
            entries = _rss_entries(url, max_per)
            for e in entries:
                title = _strip(e.get("title") or "")
                if not title:
                    continue
                src, clean = name, title
                m = re.match(r"^(.*?)\s+-\s+([^-]+)$", title)
                if m and not has_summary:  # Google 新聞標題常帶 " - 來源"
                    clean, src = m.group(1).strip(), m.group(2).strip()
                if NOISE.search(clean):
                    continue
                summary = _summarize(e.get("summary") or e.get("description") or "") if has_summary else ""
                if summary and summary[:12] == clean[:12]:
                    summary = ""  # 摘要與標題重複則不顯示
                key = re.sub(r"\s+", " ", clean.lower())
                if key in seen:
                    continue
                if kw and not kw.search("{} {}".format(clean, summary)):
                    continue
                seen.add(key)
                dt = _parse_time(e)
                out.append(
                    {
                        "title": clean,
                        "summary": summary,
                        "source": src,
                        "url": e.get("link") or "",
                        "time": dt.isoformat() if dt else now_iso(),
                        "_ts": dt.timestamp() if dt else 0,
                    }
                )
        except Exception as ex:
            print("  [warn] {}: {}".format(name, ex))
    return out
