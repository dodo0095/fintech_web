"""/backtest/ 頁面與 API。

GET  /backtest/                 頁面
GET  /backtest/api/search?q=    股票自動完成
POST /backtest/api/run          執行回測（JSON）
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import date

import pandas as pd
from django.core.cache import cache
from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from news import tickers

from .engine import (
    INDICATORS,
    OPERATORS,
    RISK_FIELDS,
    Settings,
    StrategyError,
    run_backtest,
    validate_strategy,
    warmup_days,
)
from .presets import PRESETS
from .prices import PriceError, get_prices, get_prices_any

log = logging.getLogger(__name__)

BENCHMARK_SYMBOL = "0050.TW"
EARLIEST = date(2000, 1, 1)
MAX_BODY = 32 * 1024
RATE_LIMIT = 30  # 每個 IP 每 RATE_WINDOW 秒最多幾次回測
RATE_WINDOW = 600
MAX_CONCURRENT = 3  # 同時執行的回測上限（waitress 只有 12 條 thread）
_slots = threading.BoundedSemaphore(MAX_CONCURRENT)


def _err(msg: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"ok": False, "error": msg}, status=status, json_dumps_params={"ensure_ascii": False})


def _client_ip(request: HttpRequest) -> str:
    # Caddy 會把真實來源 IP 放進 X-Forwarded-For（不信任外部傳入的值）
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (xff.split(",")[0].strip() if xff else "") or request.META.get("REMOTE_ADDR", "") or "unknown"


def _rate_limited(request: HttpRequest) -> bool:
    key = "bt:rate:" + _client_ip(request)
    if cache.add(key, 1, RATE_WINDOW):
        return False
    try:
        n = cache.incr(key)
    except ValueError:  # 剛好過期
        cache.add(key, 1, RATE_WINDOW)
        return False
    return n > RATE_LIMIT


def _parse_date(value, default: date) -> date:
    if not value:
        return default
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        raise StrategyError(f"日期格式錯誤：{value}") from None


def _num_setting(raw: dict, key: str, default: float, lo: float, hi: float, label: str) -> float:
    v = raw.get(key, default)
    if v in (None, ""):
        return default
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise StrategyError(f"{label}需要是數字") from None
    if not (lo <= f <= hi):
        raise StrategyError(f"{label}需介於 {lo:g}～{hi:g}")
    return f


def _page_meta() -> dict:
    return {
        "indicators": INDICATORS,
        "operators": OPERATORS,
        "risk_fields": {k: {"label": v[0], "min": v[1], "max": v[2]} for k, v in RISK_FIELDS.items()},
        "presets": PRESETS,
        "earliest": EARLIEST.isoformat(),
        "today": date.today().isoformat(),
    }


@ensure_csrf_cookie
@require_GET
def index(request: HttpRequest):
    return render(request, "backtest/index.html", {"meta_json": _page_meta()})


@require_GET
def api_search(request: HttpRequest):
    q = (request.GET.get("q") or "").strip()[:20]
    results = tickers.search(q, limit=10) if q else []
    return JsonResponse(
        {"results": [{"code": r["code"], "name": r["name"], "market": r["market"]} for r in results]},
        json_dumps_params={"ensure_ascii": False},
    )


@require_POST
def api_run(request: HttpRequest):
    if len(request.body) > MAX_BODY:
        return _err("請求內容過大", 413)
    try:
        body = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return _err("請求格式錯誤")
    if not isinstance(body, dict):
        return _err("請求格式錯誤")

    try:
        strategy = validate_strategy(body.get("strategy"))

        info = tickers.lookup(str(body.get("symbol") or "")[:20])
        if not info or not info.get("code"):
            raise StrategyError("請選擇要回測的股票")

        today = date.today()
        start = _parse_date(body.get("start"), date(today.year - 5, today.month, 1))
        end = _parse_date(body.get("end"), today)
        start = max(start, EARLIEST)
        end = min(end, today)
        if (end - start).days < 60:
            raise StrategyError("回測區間至少要 2 個月")

        raw_settings = body.get("settings") or {}
        if not isinstance(raw_settings, dict):
            raise StrategyError("交易設定格式錯誤")
        settings = Settings(
            capital=_num_setting(raw_settings, "capital", 1_000_000, 10_000, 100_000_000, "初始資金"),
            fee_discount=_num_setting(raw_settings, "fee_discount", 0.6, 0, 1, "手續費折扣"),
            slippage_pct=_num_setting(raw_settings, "slippage_pct", 0.1, 0, 3, "滑價"),
            board_lot=bool(raw_settings.get("board_lot")),
            is_etf=info["code"].startswith("00"),
        )
    except StrategyError as exc:
        return _err(str(exc))

    if _rate_limited(request):
        return _err("回測次數太頻繁，請稍後再試", 429)
    if not _slots.acquire(timeout=20):
        return _err("目前使用人數較多，請稍後再試", 503)
    try:
        try:
            df, pinfo = get_prices_any(tickers.yahoo_candidates(info))
        except PriceError as exc:
            return _err(str(exc), 502)

        try:
            bench_df, _ = get_prices(BENCHMARK_SYMBOL)
            bench = bench_df["close"]
        except PriceError:
            bench = None  # 基準抓不到不影響主回測

        first_bar = df.index[0].date()
        start_ts = pd.Timestamp(max(start, first_bar))
        end_ts = pd.Timestamp(end)
        # 暖機：保留 start 之前 warmup 筆資料給指標
        pos = int(df.index.searchsorted(start_ts))
        df = df.iloc[max(0, pos - warmup_days(strategy)):]

        try:
            result = run_backtest(df, strategy, settings, start_ts, end_ts,
                                  benchmark=bench, benchmark_label="0050 元大台灣50")
        except StrategyError as exc:
            return _err(str(exc))
        except Exception:
            log.exception("backtest failed: %s", info.get("code"))
            return _err("回測計算發生錯誤，請調整條件後再試", 500)
    finally:
        _slots.release()

    notes = []
    if start < first_bar:
        notes.append(f"此股票最早資料為 {first_bar}，已自動從該日開始回測")
    if pinfo.get("stale"):
        notes.append("行情暫時無法更新，本次使用較舊的快取資料")
    if result.get("missed_limit_up"):
        notes.append(f"有 {result['missed_limit_up']} 次訊號因一字漲停買不到而略過")

    result.update({
        "ok": True,
        "stock": {"code": info["code"], "name": info.get("name") or info["code"],
                  "market": info.get("market", ""), "symbol": pinfo["symbol"], "is_etf": settings.is_etf},
        "data_updated_at": pinfo["updated_at"].isoformat(),
        "notes": notes,
    })
    return JsonResponse(result, json_dumps_params={"ensure_ascii": False})
