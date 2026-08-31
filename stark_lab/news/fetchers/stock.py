"""任意台股個股新聞 → payload（泛化原 tsmc fetcher）。"""
from __future__ import annotations

import re

from news.heat_v1 import annotate_items
from news.tickers import default_focus, lookup
from .common import now_iso
from .news_common import cnyes, enrich, fetch, gnews

# 財經語境詞：短名公司（如「大樹」「台泥」）易撞地名／慣用語，
# 需標題或摘要同時帶有下列語境詞，才視為真正的個股新聞。
_CONTEXT_RE = re.compile(
    r"股價|股票|個股|盤中|盤後|開盤|收盤|漲停|跌停|漲幅|跌幅|大漲|大跌|走勢|"
    r"營收|財報|法說|法人|外資|投信|自營商|三大法人|董事|股東|除權|除息|配息|配股|"
    r"減資|增資|掛牌|上市|上櫃|興櫃|目標價|評等|毛利|每股|EPS|本益比|市值|"
    r"獲利|虧損|營益|季增|年增|月營收|殖利率|認購|認售|概念股|籌碼|成交量|"
    r"股利|季報|年報|財測|報酬率|-KY|ADR|"
    # 商業／營運語境（讓辨識度高的 2 字實名公司保住召回）
    r"出貨|量產|產能|接單|訂單|客戶|布局|擴產|新廠|簽約|併購|入股|研發|供應鏈|"
    r"代工|報價|拉貨|旺季|營運|業績|市占|市佔|接獲|標案|投資案|擴廠|轉投資",
    re.I,
)

# 名字後常見的公司尾綴，出現代表確實在講該公司（如「大樹藥局」「台積電子」）
_SUFFIX = (
    "藥局|生技|醫藥|醫療|製藥|控股|工業|科技|電子|半導體|光電|材料|金控|"
    "銀行|證券|保險|實業|建設|營造|開發|投資|國際|企業|股份|公司"
)


def _relevant(text: str, name: str, code: str) -> bool:
    """個股新聞相關性閘門：擋掉只是字面命中短名的無關新聞。

    命中規則（任一成立即相關）：
    1. 股號以獨立 token 出現（如「（6469）」「6469-KY」）—— 最強訊號。
    2. 公司名為 3 字以上（辨識度高），字面出現即算。
    3. 短名（<=2 字，最易撞地名／慣用語）出現，但需同時具備財經／商業
       語境詞、股號、或名字接公司尾綴，才算相關。
    """
    t = text or ""
    # 1) 股號帶邊界（避免 26469／64690 這種誤命中）
    if code and re.search(r"(?<![0-9A-Za-z])" + re.escape(code) + r"(?![0-9A-Za-z])", t):
        return True
    if not name or name not in t:
        return False
    # 2) 長名辨識度足夠
    if len(name) >= 3:
        return True
    # 3) 短名（2 字）需語境佐證
    if _CONTEXT_RE.search(t):
        return True
    if re.search(re.escape(name) + r"(?:" + _SUFFIX + r")", t):
        return True
    return False


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

    kw_parts = [re.escape(code)]
    if name:
        kw_parts.insert(0, re.escape(name))
    if code == "2330":
        kw_parts.append("TSMC")
    keyword = "|".join(p for p in kw_parts if p)
    if code == "2330":
        gq = "台積電 OR TSMC OR 2330 when:2d"
    elif name:
        gq = "{} OR {} when:2d".format(name, code)
    else:
        gq = "{} when:2d".format(code)

    sources = [
        ("鉅亨網", cnyes("tw_stock")),
        ("鉅亨網", cnyes("headline")),
        ("Google 新聞", gnews(gq)),
    ]
    items = fetch(sources, keyword=keyword, max_per=60)
    # 相關性閘門：擋掉只是字面撞到短公司名（地名／慣用語）的無關新聞
    items = [
        it for it in items
        if _relevant("{} {}".format(it["title"], it.get("summary") or ""), name, code)
    ]
    if not items:
        return {
            "updated_at": now_iso(),
            "symbol": yahoo,
            "name": name or code,
            "code": code,
            "items": [],
        }

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
