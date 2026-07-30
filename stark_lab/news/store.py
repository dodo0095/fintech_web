"""payload <-> DB 儲存 / 讀取層。

- writer：把 fetcher / 種子 JSON 的 payload 寫進 models（單一 feed 用交易包住）
- reader：從 models 重建「與原 data/*.json 逐欄位一致」的 payload 供 DRF 輸出

供 update_news（即時抓取）與 import_news_json（種子匯入）共用，並被 views 引用。
"""
from __future__ import annotations

from django.db import transaction

from news.models import Snapshot, NewsItem, MarketEvent, WatchlistItem, Valuation


def _num(v):
    """整數保真：把 175000.0 還原成 175000，None 維持 None，其餘原樣。"""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return v
    if f == int(f):
        return int(f)
    return f


def _set_snapshot(kind, payload):
    Snapshot.objects.update_or_create(kind=kind, defaults={"payload": payload})


def _get_snapshot(kind, default=None):
    obj = Snapshot.objects.filter(kind=kind).first()
    return obj.payload if obj else (default if default is not None else {})


# ---------------- market / heat / status / summary（整包 Snapshot） ----------------

def store_market(payload):
    _set_snapshot("market", payload)


def read_market():
    return _get_snapshot("market")


def store_heat(payload):
    _set_snapshot("heat", payload)


def read_heat():
    return _get_snapshot("heat")


def store_status(payload):
    _set_snapshot("status", payload)


def read_status():
    return _get_snapshot("status")


def store_summary(payload):
    _set_snapshot("summary", payload)


def read_summary():
    return _get_snapshot("summary")


# ---------------- 新聞類（NewsItem rows + *_meta Snapshot） ----------------

def _store_news(category, payload, meta_kind, meta_extra_keys=()):
    items = payload.get("items") or []
    with transaction.atomic():
        NewsItem.objects.filter(category=category).delete()
        objs = []
        for it in items:
            objs.append(NewsItem(
                category=category,
                rank=it.get("rank", 0),
                title=it.get("title", ""),
                summary=it.get("summary", "") or "",
                source=it.get("source", "") or "",
                url=it.get("url", "") or "",
                time=it.get("time", "") or "",
                tags=it.get("tags", []) or [],
                stance=it.get("stance"),
            ))
        NewsItem.objects.bulk_create(objs)
        meta = {"updated_at": payload.get("updated_at", "")}
        for k in meta_extra_keys:
            meta[k] = payload.get(k)
        _set_snapshot(meta_kind, meta)


def _read_news(category, meta_kind, item_fields, extra_top=()):
    meta = _get_snapshot(meta_kind, {})
    out = {"updated_at": meta.get("updated_at", "")}
    for k in extra_top:
        out[k] = meta.get(k)
    items = []
    for n in NewsItem.objects.filter(category=category).order_by("rank"):
        row = {}
        for f in item_fields:
            row[f] = getattr(n, f)
        items.append(row)
    out["items"] = items
    return out


def store_headlines(payload):
    _store_news(NewsItem.CATEGORY_HEADLINE, payload, "headlines_meta")


def read_headlines():
    return _read_news(
        NewsItem.CATEGORY_HEADLINE, "headlines_meta",
        ["rank", "title", "summary", "source", "url", "time", "tags"],
    )


def store_tsmc(payload):
    _store_news(NewsItem.CATEGORY_TSMC, payload, "tsmc_meta", meta_extra_keys=("symbol", "name"))


def read_tsmc():
    return _read_news(
        NewsItem.CATEGORY_TSMC, "tsmc_meta",
        ["rank", "title", "summary", "source", "url", "time"],
        extra_top=("symbol", "name"),
    )


def store_fed(payload):
    _store_news(NewsItem.CATEGORY_FED, payload, "fed_meta")


def read_fed():
    return _read_news(
        NewsItem.CATEGORY_FED, "fed_meta",
        ["rank", "title", "summary", "source", "url", "time", "stance"],
    )


# ---------------- 事件（MarketEvent rows + meta） ----------------

def store_events(payload):
    events = payload.get("events") or []
    with transaction.atomic():
        MarketEvent.objects.all().delete()
        objs = []
        for e in events:
            objs.append(MarketEvent(
                name=e.get("name", ""),
                date=e.get("date", ""),
                actual=e.get("actual"),
                forecast=e.get("forecast"),
                previous=e.get("previous"),
                unit=e.get("unit", "") or "",
                note=e.get("note", "") or "",
                visible=bool(e.get("visible", True)),
            ))
        MarketEvent.objects.bulk_create(objs)
        _set_snapshot("events_meta", {"updated_at": payload.get("updated_at", "")})


def read_events():
    meta = _get_snapshot("events_meta", {})
    events = []
    for e in MarketEvent.objects.all().order_by("date"):
        events.append({
            "name": e.name,
            "date": e.date,
            "actual": _num(e.actual),
            "forecast": _num(e.forecast),
            "previous": _num(e.previous),
            "unit": e.unit,
            "note": e.note,
            "visible": e.visible,
        })
    return {"updated_at": meta.get("updated_at", ""), "events": events}


# ---------------- 觀察名單（WatchlistItem rows + meta） ----------------

def store_watchlist(payload):
    items = payload.get("items") or []
    with transaction.atomic():
        WatchlistItem.objects.all().delete()
        objs = []
        for i, it in enumerate(items):
            objs.append(WatchlistItem(
                code=it.get("code", ""),
                symbol=it.get("symbol", ""),
                name=it.get("name", ""),
                position=i,
            ))
        WatchlistItem.objects.bulk_create(objs)
        _set_snapshot("watchlist_meta", {"updated_at": payload.get("updated_at", "")})


def read_watchlist():
    meta = _get_snapshot("watchlist_meta", {})
    items = [{"code": w.code, "symbol": w.symbol, "name": w.name}
             for w in WatchlistItem.objects.all().order_by("position")]
    return {"updated_at": meta.get("updated_at", ""), "items": items}


# ---------------- 估值河流圖（Valuation rows + default meta） ----------------

def store_valuation(code, payload):
    Valuation.objects.update_or_create(
        code=code,
        defaults={"updated_at": payload.get("updated_at", ""), "payload": payload},
    )


def set_default_valuation(code):
    _set_snapshot("valuation_meta", {"default_code": code})


def read_valuation(code=None):
    if code is None:
        meta = _get_snapshot("valuation_meta", {})
        code = meta.get("default_code")
        if not code:
            first = Valuation.objects.order_by("code").first()
            code = first.code if first else None
    if not code:
        return None
    obj = Valuation.objects.filter(code=code).first()
    return obj.payload if obj else None
