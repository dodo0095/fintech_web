"""自動生成「全球經濟局勢 / 一早摘要」(global) 與「今日盤勢 / 重點整理」(support)。

依現有 market / heat / valuation 資料組出數據衍生的摘要句，取代原本人工維護的
summary.json。純數據描述、非投資建議。輸出結構與原 summary.json 相容：
    {updated_at, note, global:[...], support:[...]}
"""
from __future__ import annotations

from .common import now_iso, safe_float


def _fmt_pct(v):
    v = safe_float(v)
    if v is None:
        return "—"
    return ("+%.2f%%" % v) if v >= 0 else ("%.2f%%" % v)


def build(market=None, heat=None, valuation=None) -> dict:
    market = market or {}
    heat = heat or {}
    valuation = valuation or {}

    us = market.get("indices") or []
    tw = market.get("tw_indices") or []
    us_named = {x.get("name"): x for x in us}
    tw_named = {x.get("name"): x for x in tw}

    # ---------- global：全球經濟局勢 ----------
    glob = []
    us_pcts = [safe_float(x.get("change_pct")) for x in us if x.get("symbol") != "TSM"]
    us_pcts = [p for p in us_pcts if p is not None]
    if us_pcts:
        ups = sum(1 for p in us_pcts if p > 0)
        downs = sum(1 for p in us_pcts if p < 0)
        if ups and downs:
            trend = "漲跌互見"
        elif ups:
            trend = "多數走高"
        elif downs:
            trend = "多數走低"
        else:
            trend = "多數持平"
        parts = []
        for nm in ("道瓊", "納斯達克", "S&P 500"):
            x = us_named.get(nm)
            if x:
                parts.append("%s %s" % (nm, _fmt_pct(x.get("change_pct"))))
        glob.append("美股主要指數%s（%s）。" % (trend, "、".join(parts)))

    tsm = us_named.get("台積電 ADR")
    if tsm:
        glob.append("台積電 ADR 收 %s（%s）。" % (tsm.get("value"), _fmt_pct(tsm.get("change_pct"))))

    twii = tw_named.get("加權指數")
    if twii:
        glob.append("台股加權指數 %s（%s）。" % (twii.get("value"), _fmt_pct(twii.get("change_pct"))))

    tsmc_tw = tw_named.get("台積電")
    if tsmc_tw and tsmc_tw.get("note"):
        glob.append("台積電現股 %s，%s。" % (tsmc_tw.get("value"), tsmc_tw.get("note")))

    # ---------- support：今日盤勢重點 ----------
    support = []
    all_pcts = [safe_float(x.get("change_pct")) for x in (us + tw)]
    all_pcts = [p for p in all_pcts if p is not None]
    if all_pcts:
        avg = sum(all_pcts) / len(all_pcts)
        mood = "偏多走揚" if avg > 0.3 else "偏弱承壓" if avg < -0.3 else "平盤震盪"
        support.append("美台主要指數平均 %s，大盤%s。" % (_fmt_pct(avg), mood))

    if heat.get("score") is not None:
        support.append("消息面熱度 %s（%s）。" % (heat.get("score"), heat.get("level", "")))
        for d in (heat.get("drivers") or [])[:2]:
            support.append("%s。" % d)

    if valuation:
        pe = valuation.get("current_pe")
        if pe is not None:
            support.append("%s 本益比 %s，落在%s。" % (
                valuation.get("name", ""), pe, valuation.get("zone_label", "")))

    if not glob:
        glob.append("市場資料更新中，稍後再看。")
    if not support:
        support.append("盤勢資料更新中，稍後再看。")

    return {
        "updated_at": now_iso(),
        "note": "本區由市場數據自動生成 · 非投資建議",
        "global": glob,
        "support": support,
    }
