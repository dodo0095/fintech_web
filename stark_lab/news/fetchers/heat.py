"""消息面熱度（風險溫度計）→ heat payload。

用 heat_v1 對美股頭條 + 聯準會 + 個股專區標題打分。
指針 0–100 是風險熱度（關稅／戰爭越高越熱），不再混大盤或 Fed 鴿鷹加權。
"""
from __future__ import annotations

from news.heat_v1 import (
    annotate_items,
    decide_trend,
    has_name_lock,
    has_war_event,
    map_gauge,
    score_titles,
)
from .common import now_iso


def titles_of(payload) -> list:
    return [it.get("title") or "" for it in (payload or {}).get("items") or []]


def _drivers(scored, trend, war, nlock, prev_score, news_score) -> list:
    out = []
    if war:
        out.append("戰爭級消息")
    if nlock:
        out.append("個股管制／制裁")
    if trend == "unknown":
        out.append("新聞來源失敗")
    elif trend == "cooling":
        out.append("較上次降溫")
    elif trend == "severe":
        out.append("風險熱度嚴重")
    elif trend == "hot":
        out.append("消息面偏熱")
    elif trend == "cool":
        out.append("消息面相對冷靜")
    for w in (scored.get("off_words") or [])[:2]:
        tag = "風險詞：%s" % w
        if tag not in out:
            out.append(tag)
    for w in (scored.get("on_words") or [])[:1]:
        tag = "降溫詞：%s" % w
        if tag not in out:
            out.append(tag)
    if prev_score is not None and news_score is not None and prev_score != news_score:
        delta = news_score - prev_score
        out.append("較上次 %s%+d" % (prev_score, delta))
    if not out:
        out.append("消息面平淡")
    return out[:4]


def build(news=None, tsmc=None, fed=None, prev=None, name_code="2330", name_name="台積電") -> dict:
    news = news or {}
    tsmc = tsmc or {}
    fed = fed or {}
    prev = prev or {}

    # annotate copies so callers that persist headlines/fed/tsmc get tags
    if news.get("items"):
        annotate_items(news["items"])
    if fed.get("items"):
        annotate_items(fed["items"])
    if tsmc.get("items"):
        annotate_items(tsmc["items"], name_name, name_code)

    titles = titles_of(news) + titles_of(fed) + titles_of(tsmc)
    fetched = bool(titles)
    scored = score_titles(titles)
    news_score = int(scored.get("news_score") or 0) if fetched else None
    prev_score = prev.get("news_score")
    try:
        prev_score = int(prev_score) if prev_score is not None and prev_score != "" else None
    except (TypeError, ValueError):
        prev_score = None

    if not fetched:
        trend, reason = "unknown", "新聞來源失敗"
    else:
        trend, reason = decide_trend(news_score, prev_score)

    war, war_t = has_war_event(scored.get("unique_titles") or titles)
    nlock, nlock_t = has_name_lock(scored.get("unique_titles") or titles, name_name, name_code)
    gauge, level = map_gauge(news_score if fetched else None, trend)
    macro = score_titles(titles_of(news) + titles_of(fed))
    name = score_titles(titles_of(tsmc))

    return {
        "updated_at": now_iso(),
        "algo": "heat_v1",
        "score": gauge,
        "level": level,
        "news_score": 0 if news_score is None else news_score,
        "trend": trend,
        "prev_score": prev_score,
        "reason": reason,
        "war_lock": bool(war),
        "name_lock": bool(nlock),
        "lock_title": war_t or nlock_t,
        "name_code": name_code,
        "name_name": name_name,
        "components": {
            "macro_score": int(macro.get("news_score") or 0),
            "name_score": int(name.get("news_score") or 0),
            "n_unique": scored.get("n_unique", 0),
        },
        "drivers": _drivers(scored, trend, war, nlock, prev_score, news_score),
    }
