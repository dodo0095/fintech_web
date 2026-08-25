"""heat_v1 — small rule model for news risk heat.

Ported from the paper-trading scorer (no journal, no TWII pause, no broker).
Positive weight = risk heat. Negative = cooling.
"""
from __future__ import annotations

import math
import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

WEIGHTS: List[Tuple[str, int]] = [
    ("全面性關稅", 2),
    ("出口管制", 2),
    ("取消關稅", -2),
    ("pause tariff", -2),
    ("export control", 2),
    ("exemption", -2),
    ("ceasefire", -2),
    ("invasion", 3),
    ("blockade", 3),
    ("sanction", 2),
    ("embargo", 2),
    ("hawkish", 1),
    ("selloff", 2),
    ("missile", 3),
    ("dovish", -2),
    ("tariff", 1),
    ("truce", -2),
    ("trade deal", -1),
    ("peace deal", -1),
    ("war", 3),
    ("加徵", 2),
    ("制裁", 2),
    ("禁運", 2),
    ("戰爭", 3),
    ("衝突", 2),
    ("導彈", 3),
    ("封鎖", 3),
    ("入侵", 3),
    ("衰退", 2),
    ("恐慌", 2),
    ("暴跌", 2),
    ("崩跌", 2),
    ("升息", 1),
    ("鷹派", 1),
    ("降息", -2),
    ("協議", -1),
    ("休戰", -2),
    ("豁免", -2),
    ("利多", -1),
    ("鴿派", -2),
    ("暫緩", -1),
    ("taco", -2),
    ("踩剎車", -2),
    ("談妥", -1),
    ("降至", -1),
    ("調降", -1),
    ("降低關稅", -2),
    ("關稅", 1),
]

_TARIFF_GENERIC = ("關稅", "tariff")
_TARIFF_COOL = (
    "taco",
    "踩剎車",
    "降至",
    "調降",
    "降低關稅",
    "取消關稅",
    "pause tariff",
    "豁免",
    "暫緩",
    "談妥",
    "協議",
    "違憲",
    "exemption",
    "trade deal",
)
_COMMENTARY = (
    "一文看",
    "一文看懂",
    "有哪些風險",
    "有哪些多重風險",
    "什麼是關稅",
)

WAR_PHRASES = (
    "invasion",
    "blockade",
    "missile",
    "war",
    "戰爭",
    "導彈",
    "封鎖",
    "入侵",
)
NAME_LOCK_PHRASES = (
    "出口管制",
    "禁運",
    "制裁",
    "export control",
    "embargo",
    "sanction",
)

TITLE_HEAT_CAP = 4
HOT = 6
SEVERE = 12
COOLING_DROP = 3

LEVEL_LABEL = {
    "cool": "冷靜",
    "cooling": "降溫中",
    "hot": "偏熱",
    "severe": "嚴重",
    "unknown": "未知",
}

_PUBLISHER = re.compile(r"\s+[-–—|]\s+\S+\s*$")
_NOISE = re.compile(r"[^\w\u4e00-\u9fff]+", re.UNICODE)


def normalize_title(title: str) -> str:
    t = re.sub(r"\s+", " ", (title or "")).strip()
    t = _PUBLISHER.sub("", t).strip()
    return t.lower()


def title_key(title: str) -> str:
    return _NOISE.sub("", normalize_title(title))


def _is_ascii_phrase(phrase: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9 \-]+", phrase.lower()))


def phrase_in_title(text: str, phrase: str) -> bool:
    p = phrase.lower()
    if _is_ascii_phrase(p):
        return re.search(r"\b" + re.escape(p) + r"s?\b", text) is not None
    return p in text


def headline_heat(title: str) -> Tuple[int, List[str], List[str]]:
    """(capped_heat, risk_words, cooling_words). Longest match wins."""
    key = normalize_title(title)
    if any(c in key for c in _COMMENTARY):
        return 0, [], []
    found: List[Tuple[str, int]] = []
    for phrase, w in WEIGHTS:
        if phrase_in_title(key, phrase):
            found.append((phrase, w))
    if any(phrase_in_title(key, c) for c in _TARIFF_COOL):
        found = [(p, w) for p, w in found if p.lower() not in _TARIFF_GENERIC]
    kept: List[Tuple[str, int]] = []
    for phrase, w in found:
        p = phrase.lower()
        if any(p != other.lower() and p in other.lower() for other, _ in found):
            continue
        kept.append((phrase, w))
    raw = 0
    off: List[str] = []
    on: List[str] = []
    for phrase, w in kept:
        raw += w
        if w > 0:
            off.append(phrase)
        else:
            on.append(phrase)
    heat = max(-TITLE_HEAT_CAP, min(TITLE_HEAT_CAP, raw))
    return heat, off, on


def score_titles(titles: Sequence[str]) -> Dict:
    seen = set()
    unique: List[str] = []
    heat = 0
    off_hits: List[str] = []
    on_hits: List[str] = []
    off_words: List[str] = []
    on_words: List[str] = []
    for t in titles:
        k = title_key(t)
        if not k or k in seen:
            continue
        seen.add(k)
        unique.append(t)
        h, off, on = headline_heat(t)
        heat += h
        off_words.extend(off)
        on_words.extend(on)
        if h > 0:
            off_hits.append(t)
        elif h < 0:
            on_hits.append(t)
    return {
        "news_score": int(heat),
        "n_unique": len(unique),
        "n_raw": len(titles),
        "off_headlines": off_hits[:8],
        "on_headlines": on_hits[:8],
        "unique_titles": unique[:40],
        "off_words": _uniq(off_words),
        "on_words": _uniq(on_words),
    }


def _uniq(xs: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for x in xs:
        k = x.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(x)
    return out


def has_war_event(titles: Optional[Sequence[str]]) -> Tuple[bool, str]:
    for t in titles or []:
        key = normalize_title(t)
        for phrase in WAR_PHRASES:
            if phrase_in_title(key, phrase):
                return True, t
    return False, ""


def _mentions_name(title: str, name: str, ticker: str) -> bool:
    key = normalize_title(title)
    n = normalize_title(name or "")
    if n and n in key:
        return True
    code = (ticker or "").split(".")[0].lower()
    return bool(code) and code in key


def has_name_lock(titles: Optional[Sequence[str]], name: str, ticker: str) -> Tuple[bool, str]:
    for t in titles or []:
        if not _mentions_name(t, name, ticker):
            continue
        key = normalize_title(t)
        for phrase in NAME_LOCK_PHRASES:
            if phrase_in_title(key, phrase):
                return True, t
    return False, ""


def decide_trend(curr: Optional[int], prev: Optional[int]) -> Tuple[str, str]:
    if curr is None:
        return "unknown", "無分數"
    if prev is None:
        if curr >= SEVERE:
            return "severe", "熱度 %s ≥ 嚴重線 %s" % (curr, SEVERE)
        if curr >= HOT:
            return "hot", "熱度 %s ≥ %s" % (curr, HOT)
        return "cool", "熱度 %s < %s" % (curr, HOT)
    delta = curr - prev
    if curr >= SEVERE:
        return "severe", "熱度 %s ≥ 嚴重線 %s（上次 %s，Δ%+d）" % (curr, SEVERE, prev, delta)
    if curr < HOT:
        return "cool", "熱度 %s < %s（上次 %s，Δ%+d）" % (curr, HOT, prev, delta)
    if prev - curr >= COOLING_DROP:
        return "cooling", "仍偏熱 %s 但較上次 %s 降溫" % (curr, prev)
    return "hot", "仍熱且未明顯降溫：上次 %s 本次 %s（Δ%+d）" % (prev, curr, delta)


def map_gauge(news_score: Optional[int], trend: str) -> Tuple[int, str]:
    """0–100 needle. Saturates in severe so 12 and 36 are distinguishable."""
    level = LEVEL_LABEL.get(trend, "未知")
    if trend == "unknown" or news_score is None:
        return 50, level
    s = float(news_score)
    if trend == "cool":
        score = 20.0 + s * (15.0 / 6.0)
        score = max(0.0, min(35.0, score))
    elif trend == "cooling":
        t = 1.0 / (1.0 + math.exp(-(s - 8.0) / 4.0))
        score = 36.0 + t * 19.0
    elif trend == "hot":
        t = max(0.0, min(1.0, (s - 6.0) / 6.0))
        score = 56.0 + t * 23.0
    else:
        extra = max(0.0, s - 12.0)
        score = 80.0 + 20.0 * (1.0 - math.exp(-extra / 12.0))
    return int(round(score)), level


def annotate_item(item: Dict, name: str = "", ticker: str = "") -> Dict:
    title = item.get("title") or ""
    h, off, on = headline_heat(title)
    item["heat"] = h
    item["hits_off"] = off
    item["hits_on"] = on
    war, _ = has_war_event([title])
    nlock, _ = has_name_lock([title], name, ticker) if (name or ticker) else (False, "")
    item["war"] = bool(war)
    item["name_lock"] = bool(nlock)
    return item


def annotate_items(items: Sequence[Dict], name: str = "", ticker: str = "") -> List[Dict]:
    out = []
    for it in items or []:
        out.append(annotate_item(it, name, ticker))
    return out
