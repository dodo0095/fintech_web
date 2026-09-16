"""Backtest page. Paper reports only — never places broker orders."""
from __future__ import annotations

import json
import mimetypes
import re

from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_http_methods

from .runner import (
    backtest_root,
    load_defaults_json,
    load_report,
    load_universe_meta,
    parse_tickers_text,
    reports_dir,
    run_strategy,
    strategy_label,
    tickers_to_text,
)

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_PARAM_PREFIX = "param_"


def _clean_date(value: str) -> str:
    value = (value or "").strip()
    return value if _DATE_RE.match(value) else ""


def _clean_strategy(value: str, allowed: list[str], default: str = "breakout_v2") -> str:
    value = (value or "").strip()
    if value in allowed:
        return value
    if default in allowed:
        return default
    return allowed[0] if allowed else default


def _parse_params_json(raw: str) -> dict:
    text = (raw or "").strip()
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _coerce_param(raw: str):
    text = (raw or "").strip()
    if text == "":
        return None
    low = text.lower()
    if low in ("true", "yes", "on", "1"):
        return True
    if low in ("false", "no", "off", "0"):
        return False
    try:
        if re.fullmatch(r"-?\d+", text):
            return int(text)
        return float(text)
    except ValueError:
        return text


def _parse_param_fields(post) -> dict:
    """Collect name=param_* inputs from the form."""
    out: dict = {}
    bool_seen: set[str] = set()
    for key in post.keys():
        if not key.startswith(_PARAM_PREFIX):
            continue
        name = key[len(_PARAM_PREFIX) :]
        if not name:
            continue
        values = post.getlist(key) if hasattr(post, "getlist") else [post.get(key)]
        # checkbox pattern: hidden "false" + checkbox "true" → last wins if checked
        if len(values) > 1:
            out[name] = _coerce_param(values[-1])
            bool_seen.add(name)
            continue
        out[name] = _coerce_param(values[0] if values else "")
    return out


def _merge_params(post) -> dict:
    """param_* fields first, then params_json overlay (JS collect)."""
    params = _parse_param_fields(post)
    overlay = _parse_params_json(post.get("params_json") or "")
    if overlay:
        params.update(overlay)
    # drop pure-null noise
    return {k: v for k, v in params.items() if k}


def _base_ctx(request: HttpRequest, strategy: str, start: str, end: str, meta: dict) -> dict:
    root_s = ""
    py_s = ""
    err = meta.get("error") or ""
    try:
        from .runner import backtest_python

        root = backtest_root()
        root_s = str(root)
        py_s = str(backtest_python(root))
    except FileNotFoundError as exc:
        err = str(exc)
    defaults = meta.get("defaults") or {}
    # Ensure exported JSON is embedded even if live import failed partially.
    exported = load_defaults_json()
    if exported.get("strategies"):
        merged = dict(defaults)
        for name, payload in (exported.get("strategies") or {}).items():
            if isinstance(payload, dict):
                base = dict(merged.get(name) or {})
                base.update(payload)
                merged[name] = base
        defaults = merged
    tickers_text = meta.get("tickers_text") or ""
    if not tickers_text and isinstance(exported.get("tickers"), dict):
        tickers_text = tickers_to_text(exported["tickers"])
    return {
        "choices": meta.get("strategies") or [],
        "strategy": strategy,
        "start": start,
        "end": end,
        "backtest_python": py_s,
        "setup_error": err,
        "home_url": "/",
        "tickers_text": tickers_text,
        "refresh_data": True,
        "default_tickers_text": tickers_text,
        "param_groups": meta.get("param_groups") or [],
        "defaults_payload": defaults,
        "meta_ok": bool(meta.get("ok")),
    }


@require_http_methods(["GET", "POST"])
def index(request: HttpRequest) -> HttpResponse:
    meta = load_universe_meta()
    allowed = [s["id"] for s in (meta.get("strategies") or [])]
    strategy = _clean_strategy(
        request.POST.get("strategy") or request.GET.get("strategy") or "breakout_v2",
        allowed,
    )
    start = _clean_date(request.POST.get("start") or request.GET.get("start") or "")
    end = _clean_date(request.POST.get("end") or request.GET.get("end") or "")
    ctx = _base_ctx(request, strategy, start, end, meta)
    ctx["result"] = None
    ctx["error"] = ctx.get("setup_error") or ""
    ctx["log"] = ""
    ctx["ran"] = False
    ctx["posted_params"] = {}

    if request.method == "POST":
        posted_tickers_text = request.POST.get("tickers_text")
        if posted_tickers_text is not None:
            ctx["tickers_text"] = posted_tickers_text
        ctx["posted_params"] = _merge_params(request.POST)

    action = (request.POST.get("action") or request.GET.get("action") or "").strip()
    if request.method == "GET" and not action:
        if not ctx["error"]:
            report = load_report(strategy)
            if report.get("ok"):
                ctx["result"] = report
        return render(request, "twbacktest/index.html", ctx)

    if ctx["error"]:
        return render(request, "twbacktest/index.html", ctx)

    tickers = parse_tickers_text(ctx["tickers_text"])
    if action == "run" and not tickers:
        ctx["error"] = "股票清單是空的。請至少留一檔（代號 或 代號 名稱）。"
        return render(request, "twbacktest/index.html", ctx)

    if action == "run":
        # hidden 0 + checkbox 1 → last value wins; missing → default on
        raw_refresh = request.POST.get("refresh_data")
        if raw_refresh is None:
            refresh = True
        else:
            refresh = str(raw_refresh).lower() not in ("0", "false", "off", "no", "")
        ctx["refresh_data"] = refresh
        report = run_strategy(
            strategy,
            start=start,
            end=end,
            params=ctx["posted_params"] or None,
            tickers=tickers or None,
            refresh=refresh,
        )
        ctx["ran"] = True
        ctx["log"] = report.get("log") or ""
        if report.get("ok"):
            ctx["result"] = report
        else:
            ctx["error"] = report.get("error") or "回測失敗"
            fallback = load_report(strategy)
            if fallback.get("ok"):
                ctx["result"] = fallback
                ctx["error"] += "（下方仍顯示既有報告）"
        return render(request, "twbacktest/index.html", ctx)

    report = load_report(strategy)
    if report.get("ok"):
        ctx["result"] = report
    else:
        ctx["error"] = f"還沒有 {strategy_label(strategy)} 的報告。請按「執行回測」。"
    return render(request, "twbacktest/index.html", ctx)


@require_GET
def equity_chart(request: HttpRequest, strategy: str) -> FileResponse:
    meta = load_universe_meta()
    allowed = [s["id"] for s in (meta.get("strategies") or [])]
    strategy = _clean_strategy(strategy, allowed)
    try:
        rd = reports_dir()
    except FileNotFoundError as exc:
        raise Http404(str(exc)) from exc
    path = (rd / f"{strategy}_equity.png").resolve()
    try:
        path.relative_to(rd.resolve())
    except ValueError as exc:
        raise Http404("bad path") from exc
    if not path.is_file():
        raise Http404("尚無權益圖")
    ctype, _ = mimetypes.guess_type(str(path))
    return FileResponse(path.open("rb"), content_type=ctype or "image/png")
