"""消息面熱度（市場情緒溫度計）→ heat payload（自 fetch_heat.py 移植）。

原腳本讀 data/*.json；此處改為由呼叫端傳入已抓好的 payload dict。
"""
from __future__ import annotations

import re

from .common import now_iso, safe_float

POS = re.compile(
    r"大漲|飆|漲|創(?:新)?高|新高|樂觀|利多|強勁|看好|買超|回升|反彈|突破|"
    r"優於預期|成長|擴產|訂單|拉貨|升溫|勁揚|上揚|走高|加碼|增持|創紀錄|樂觀"
)
NEG = re.compile(
    r"大跌|重挫|下挫|跌|摔|崩|新低|悲觀|利空|疲弱|看壞|賣超|恐慌|警告|警訊|衰退|"
    r"裁員|違約|下修|不如預期|殺盤|急跌|走弱|觸礁|拋售|下滑|降評|暴雷|"
    r"虧損|震盪|危險|承壓|壓力|升息|緊縮|重摔|利空|疑慮|風險|摜壓"
)


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def sentiment_score(texts):
    net = 0
    used = 0
    for t in texts:
        p = len(POS.findall(t))
        n = len(NEG.findall(t))
        if p or n:
            used += 1
            net += 1 if p > n else -1 if n > p else 0
    if used == 0:
        return 0.5, 0
    return clamp01((net / used + 1) / 2), used


def build(news=None, tsmc=None, fed=None, market=None) -> dict:
    news = news or {}
    tsmc = tsmc or {}
    fed = fed or {}
    market = market or {}

    texts = []
    major = 0
    for it in news.get("items") or []:
        texts.append("{} {}".format(it.get("title", ""), it.get("summary", "")))
        if "重大" in (it.get("tags") or []):
            major += 1
    for it in tsmc.get("items") or []:
        texts.append(it.get("title", ""))

    senti, _used = sentiment_score(texts)
    volume = clamp01(major / 5.0)

    doves = sum(1 for i in (fed.get("items") or []) if i.get("stance") == "dove")
    hawks = sum(1 for i in (fed.get("items") or []) if i.get("stance") == "hawk")
    fed_s = 0.5 if (doves + hawks) == 0 else clamp01((doves - hawks) / (doves + hawks) / 2 + 0.5)

    idx_all = (market.get("indices") or []) + (market.get("tw_indices") or [])
    pcts = [safe_float(x.get("change_pct")) for x in idx_all]
    pcts = [p for p in pcts if p is not None]
    avg = sum(pcts) / len(pcts) if pcts else 0.0
    mkt = clamp01(avg / 4.0 + 0.5) if pcts else 0.5

    score = round((senti * 0.40 + mkt * 0.30 + volume * 0.15 + fed_s * 0.15) * 100)
    if score < 20:
        level = "冰冷"
    elif score < 40:
        level = "偏冷"
    elif score < 60:
        level = "中性"
    elif score < 80:
        level = "偏熱"
    else:
        level = "過熱"

    drivers = []
    if senti > 0.6:
        drivers.append("利多新聞偏多")
    elif senti < 0.4:
        drivers.append("利空新聞偏多")
    if pcts and avg > 0.3:
        drivers.append("大盤走揚")
    elif pcts and avg < -0.3:
        drivers.append("大盤走弱")
    if fed_s > 0.6:
        drivers.append("Fed 偏鴿")
    elif fed_s < 0.4:
        drivers.append("Fed 偏鷹")
    if volume >= 0.8:
        drivers.append("重大消息量大")
    if not drivers:
        drivers.append("消息面平淡")

    return {
        "updated_at": now_iso(),
        "score": score,
        "level": level,
        "components": {
            "sentiment": round(senti, 2),
            "market": round(mkt, 2),
            "volume": round(volume, 2),
            "fed": round(fed_s, 2),
        },
        "drivers": drivers[:3],
    }
