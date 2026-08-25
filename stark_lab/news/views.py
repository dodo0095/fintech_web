"""news app DRF 端點。

回傳原始 payload（鏡射原 data/*.json，逐欄位一致，不套公司信封層，
與既有 apiserver 風格一致）。所有端點皆為 GET。
"""
from __future__ import annotations

import threading
from datetime import datetime, timedelta

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from news import store
from news.heat_v1 import annotate_items
from news.tickers import lookup, yahoo_candidates
from news.fetchers import heat as f_heat
from news.fetchers import stock as f_stock
from news.fetchers import valuation as f_valuation
from news.fetchers.common import TW

STOCK_TTL_MIN = 15
VAL_TTL_HOURS = 6

_inflight = {}
_inflight_lock = threading.Lock()


def _parse_iso(raw):
    if not raw:
        return None
    text = str(raw).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TW)
    return dt


def _fresh(payload, minutes=None, hours=None):
    if not payload:
        return False
    dt = _parse_iso(payload.get("updated_at"))
    if not dt:
        return False
    age = datetime.now(TW) - dt.astimezone(TW)
    if minutes is not None:
        return age <= timedelta(minutes=minutes)
    return age <= timedelta(hours=hours or 0)


def _once(key, fn):
    with _inflight_lock:
        slot = _inflight.get(key)
        if slot is None:
            slot = {"event": threading.Event(), "result": None, "error": None}
            _inflight[key] = slot
            owner = True
        else:
            owner = False
    if not owner:
        slot["event"].wait(timeout=90)
        if slot["error"] is not None:
            raise slot["error"]
        return slot["result"]
    try:
        slot["result"] = fn()
        return slot["result"]
    except Exception as exc:
        slot["error"] = exc
        raise
    finally:
        slot["event"].set()
        with _inflight_lock:
            if _inflight.get(key) is slot:
                _inflight.pop(key, None)


@api_view(["GET"])
def market(request):
    return Response(store.read_market())


@api_view(["GET"])
def headlines(request):
    payload = store.read_headlines()
    annotate_items(payload.get("items") or [])
    return Response(payload)


@api_view(["GET"])
def tsmc(request):
    payload = store.read_tsmc()
    annotate_items(payload.get("items") or [], payload.get("name") or "台積電", payload.get("code") or "2330")
    return Response(payload)


@api_view(["GET"])
def fed(request):
    payload = store.read_fed()
    annotate_items(payload.get("items") or [])
    return Response(payload)


def _stock_payload(info):
    code = info["code"]
    if code == "2330":
        cached = store.read_tsmc()
        if cached and cached.get("items"):
            return cached
    snap = store.read_stock_cache(code)
    if _fresh(snap, minutes=STOCK_TTL_MIN):
        return snap

    def _fetch():
        again = store.read_stock_cache(code)
        if _fresh(again, minutes=STOCK_TTL_MIN):
            return again
        payload = f_stock.build(code=code, name=info["name"], yahoo=info["yahoo"])
        store.store_stock_cache(code, payload)
        return payload

    return _once("stock:" + code, _fetch)


def _heat_for(info):
    prev = store.read_heat() or {}
    if info["code"] == "2330" and prev.get("algo") == "heat_v1" and not info.get("_force"):
        if prev.get("name_code") in (None, "", "2330"):
            return prev
    try:
        stock = _stock_payload(info)
    except Exception:
        stock = {
            "updated_at": "",
            "symbol": info.get("yahoo") or "",
            "name": info.get("name") or "",
            "code": info["code"],
            "items": [],
        }
    return f_heat.build(
        news=store.read_headlines(),
        tsmc=stock,
        fed=store.read_fed(),
        prev=prev,
        name_code=info["code"],
        name_name=info.get("name") or info["code"],
    )


@api_view(["GET"])
def heat(request):
    raw = (request.query_params.get("code") or "").strip()
    if not raw:
        payload = store.read_heat()
        return Response(payload)
    info = lookup(raw)
    if not info:
        return Response({"detail": "查無此代碼：{}".format(raw)}, status=status.HTTP_404_NOT_FOUND)
    try:
        payload = _heat_for(info)
    except Exception as exc:
        return Response(
            {"detail": "熱度計算失敗：{}".format(exc)},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    return Response(payload)


@api_view(["GET"])
def lookup_code(request, code):
    info = lookup(code)
    if not info:
        return Response({"detail": "請輸入股票代號，例如 2317"}, status=status.HTTP_404_NOT_FOUND)
    return Response({
        "code": info["code"],
        "name": info.get("name") or "",
        "yahoo": info.get("yahoo") or "",
        "candidates": yahoo_candidates(info),
    })


@api_view(["GET"])
def stock(request, code):
    info = lookup(code)
    if not info:
        return Response({"detail": "查無此代碼：{}".format(code)}, status=status.HTTP_404_NOT_FOUND)
    try:
        payload = _stock_payload(info)
    except Exception as exc:
        return Response(
            {"detail": "新聞抓取失敗：{}".format(exc)},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    return Response(payload)


@api_view(["GET"])
def events(request):
    return Response(store.read_events())


@api_view(["GET"])
def watchlist(request):
    return Response(store.read_watchlist())


@api_view(["GET"])
def summary(request):
    return Response(store.read_summary())


@api_view(["GET"])
def status_view(request):
    return Response(store.read_status())


@api_view(["GET"])
def valuation_default(request):
    payload = store.read_valuation()
    if payload is None:
        return Response({"detail": "no valuation data"}, status=status.HTTP_404_NOT_FOUND)
    return Response(payload)


def _valuation_payload(info):
    code = info["code"]
    existing = store.read_valuation(code)
    if _fresh(existing, hours=VAL_TTL_HOURS):
        return existing

    def _build():
        again = store.read_valuation(code)
        if _fresh(again, hours=VAL_TTL_HOURS):
            return again
        payload = f_valuation.build_symbol_try(
            code, info.get("name") or code, preferred_yahoo=info.get("yahoo"),
        )
        if payload is None:
            return None
        store.store_valuation(code, payload)
        return payload

    return _once("val:" + code, _build)


@api_view(["GET"])
def valuation_by_code(request, code):
    info = lookup(code)
    if not info:
        return Response(
            {"detail": "查無此代碼：{}".format(code)},
            status=status.HTTP_404_NOT_FOUND,
        )
    try:
        payload = _valuation_payload(info)
    except Exception as exc:
        return Response(
            {"detail": "估值計算失敗：{}".format(exc)},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    if payload is None:
        return Response(
            {
                "detail": "這檔財報資料不足，暫時畫不出河流圖",
                "code": info["code"],
                "name": info["name"],
            },
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    return Response(payload)
