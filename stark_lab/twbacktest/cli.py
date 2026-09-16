#!/usr/bin/env python
"""Single-strategy backtest CLI. Run with snr_backtest's .venv python.

Does not import Django. Does not touch paper/account.json or live watchers.
Writes the same reports/ files as run.py (one strategy only).

Supports --params / --tickers overrides without writing config.py.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import fields, replace
from datetime import datetime, timezone
try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore
from pathlib import Path

ALLOWED = (
    "breakout_v1",
    "breakout_v2",
    "breakout_raw",
    "pullback_v1",
    "pullback_raw",
    "macd_v1",
    "macd_v2",
    "macd_raw",
    "rsi_v1",
    "rsi_v2",
    "rsi_raw",
    "kd_v1",
    "kd_v2",
    "kd_raw",
    "sma_v1",
    "sma_v2",
    "sma_raw",
    "bb_v1",
    "bb_v2",
    "bb_raw",
)

# StrategySpec fields we may override from --params / web form.
SPEC_OVERRIDE_KEYS = (
    "tp",
    "sl",
    "time_stop_days",
    "use_snr",
    "kind",
    "snr_min",
    "snr_rising",
    "vol_mult",
    "twii_filter",
    "no_chase",
    "chase_mult",
    "trail",
    "trail_arm",
    "trail_lookback",
)

# Extra knobs that live on config/strategies modules (not StrategySpec).
CONFIG_OVERRIDE_KEYS = ("lookback", "snr_max")


def get_spec(name: str):
    from strategies import all_strategies, make_breakout_v2

    if name == "breakout_v2":
        return make_breakout_v2()
    for spec in all_strategies():
        if spec.name == name:
            return spec
    raise SystemExit(f"unknown strategy: {name}")


def _load_json_arg(raw: str):
    """Accept inline JSON string or a path to a JSON file."""
    raw = (raw or "").strip()
    if not raw:
        return None
    path = Path(raw)
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(raw)


def _normalize_tickers(raw) -> dict[str, str]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        out = {}
        for k, v in raw.items():
            code = str(k).strip()
            if not code:
                continue
            if v is None or v is True:
                out[code] = code
            else:
                out[code] = str(v).strip() or code
        return out
    if isinstance(raw, list):
        out = {}
        for item in raw:
            if isinstance(item, dict):
                code = str(item.get("code") or item.get("ticker") or "").strip()
                name = str(item.get("name") or code).strip()
                if code:
                    out[code] = name or code
            else:
                code = str(item).strip()
                if code:
                    out[code] = code
        return out
    raise SystemExit("--tickers must be a JSON object or array")


def _coerce_value(key: str, value, sample):
    if value is None:
        return None
    if isinstance(sample, bool):
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)) and value in (0, 1):
            return bool(value)
        s = str(value).strip().lower()
        if s in ("1", "true", "yes", "on", "y"):
            return True
        if s in ("0", "false", "no", "off", "n", ""):
            return False
        raise SystemExit(f"params.{key}: expected bool, got {value!r}")
    if isinstance(sample, int) and not isinstance(sample, bool):
        return int(float(value))
    if isinstance(sample, float):
        return float(value)
    if sample is None:
        # snr_min can be None — try float, allow empty → None
        if value == "" or value is None:
            return None
        if isinstance(value, bool):
            return value
        try:
            return float(value)
        except (TypeError, ValueError):
            return value
    return value


def apply_params(spec, params: dict | None):
    """Return (spec, extras) where extras holds lookback/snr_max etc."""
    if not params:
        return spec, {}
    extras = {}
    kwargs = {}
    field_names = {f.name for f in fields(spec)}
    for key, value in params.items():
        if key in CONFIG_OVERRIDE_KEYS:
            extras[key] = value
            continue
        if key not in SPEC_OVERRIDE_KEYS or key not in field_names:
            continue
        sample = getattr(spec, key)
        kwargs[key] = _coerce_value(key, value, sample)
    if kwargs:
        spec = replace(spec, **kwargs)
    return spec, extras


def apply_config_overrides(extras: dict, tickers: dict | None) -> None:
    """Monkeypatch config (and mirrored strategies imports) for this process only."""
    import config
    import strategies

    if tickers:
        config.TICKERS = dict(tickers)
        # data/engine may have imported TICKERS by name — patch common mirrors
        for mod_name in ("data", "engine", "run", "universe"):
            mod = sys.modules.get(mod_name)
            if mod is not None and hasattr(mod, "TICKERS"):
                setattr(mod, "TICKERS", config.TICKERS)

    if "lookback" in extras and extras["lookback"] is not None and extras["lookback"] != "":
        lb = int(float(extras["lookback"]))
        config.BREAKOUT_LOOKBACK = lb
        if hasattr(strategies, "BREAKOUT_LOOKBACK"):
            strategies.BREAKOUT_LOOKBACK = lb

    if "snr_max" in extras:
        val = extras["snr_max"]
        if val is None or val == "":
            pass
        else:
            sm = float(val)
            config.PULLBACK_SNR_MAX = sm
            if hasattr(strategies, "PULLBACK_SNR_MAX"):
                strategies.PULLBACK_SNR_MAX = sm


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one snr_backtest strategy")
    parser.add_argument("--root", required=True, help="snr_backtest directory")
    parser.add_argument("--strategy", required=True, help="strategy name (see strategies.py)")
    parser.add_argument("--start", default="", help="YYYY-MM-DD (optional)")
    parser.add_argument("--end", default="", help="YYYY-MM-DD (optional)")
    parser.add_argument("--download", action="store_true", help="force Yahoo refresh")
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="cache only; never call Yahoo even if bars are short",
    )
    parser.add_argument(
        "--params",
        default="",
        help="JSON object or path to JSON file overriding StrategySpec fields",
    )
    parser.add_argument(
        "--tickers",
        default="",
        help='JSON dict code->name or list of codes (path or inline string)',
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if not (root / "run.py").exists() or not (root / "engine.py").exists():
        print(f"not an snr_backtest root: {root}", file=sys.stderr)
        return 2

    sys.path.insert(0, str(root))

    params = _load_json_arg(args.params) if args.params.strip() else None
    tickers_raw = _load_json_arg(args.tickers) if args.tickers.strip() else None
    tickers = _normalize_tickers(tickers_raw) if tickers_raw is not None else None
    if params is not None and not isinstance(params, dict):
        print("--params must be a JSON object", file=sys.stderr)
        return 2

    from config import END_DATE, INITIAL_CAPITAL, REPORTS_DIR, START_DATE, TICKERS
    from data import load_universe
    from engine import run_universe
    from run import write_strategy_reports

    def _today_tw() -> str:
        if ZoneInfo is not None:
            return datetime.now(ZoneInfo("Asia/Taipei")).strftime("%Y-%m-%d")
        return datetime.now().strftime("%Y-%m-%d")

    start = args.start.strip() or START_DATE
    # Empty end → today (TW), so server/web is not stuck on config.END_DATE.
    end = args.end.strip() or _today_tw()
    spec = get_spec(args.strategy)
    spec, extras = apply_params(spec, params)
    apply_config_overrides(extras, tickers)

    # Re-read TICKERS after possible monkeypatch
    import config as _cfg

    active_tickers = _cfg.TICKERS

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    log = logging.getLogger("twbacktest.cli")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    status_path = REPORTS_DIR / "_web_last_run.json"
    status_path.write_text(
        json.dumps(
            {
                "ok": False,
                "running": True,
                "strategy": spec.name,
                "start": start,
                "end": end,
                "params": params or {},
                "tickers": list(active_tickers.keys()) if isinstance(active_tickers, dict) else active_tickers,
                "started_at": stamp,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    cache_only = bool(getattr(args, "no_download", False))
    force = bool(args.download) and not cache_only
    log.info(
        "loading universe  force=%s  cache_only=%s  end=%s  tickers=%d",
        force,
        cache_only,
        end,
        len(active_tickers),
    )
    try:
        prices, failed = load_universe(
            force_download=force,
            end_date=end,
            cache_only=cache_only,
        )
    except TypeError:
        prices, failed = load_universe(force_download=force)
    ok_n = sum(1 for t in active_tickers if t in prices)
    log.info("prices ready: %d/%d  failed=%s", ok_n, len(active_tickers), failed)
    if ok_n == 0:
        status_path.write_text(
            json.dumps(
                {
                    "ok": False,
                    "running": False,
                    "strategy": spec.name,
                    "error": "no price data",
                    "failed": failed,
                    "finished_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return 1

    log.info(
        "backtest %s  %s → %s  tp=%s sl=%s use_snr=%s",
        spec.name,
        start,
        end,
        spec.tp,
        spec.sl,
        spec.use_snr,
    )
    results = run_universe(prices, spec, INITIAL_CAPITAL, start, end)
    summary, comb = write_strategy_reports(spec, results)
    ew = summary[summary["ticker"] == "EQUAL_WEIGHT"]
    row = ew.iloc[0].to_dict() if not ew.empty else {}
    # json-friendly
    clean = {}
    for k, v in row.items():
        try:
            if hasattr(v, "item"):
                v = v.item()
        except Exception:
            pass
        if isinstance(v, float):
            clean[k] = None if (v != v) else v  # NaN
        else:
            clean[k] = v if isinstance(v, (str, int, bool, type(None))) else str(v)

    payload = {
        "ok": True,
        "running": False,
        "strategy": spec.name,
        "start": start,
        "end": end,
        "params": params or {},
        "tickers": list(active_tickers.keys()) if isinstance(active_tickers, dict) else active_tickers,
        "failed": failed,
        "equal_weight": clean,
        "finished_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "reports_dir": str(REPORTS_DIR),
    }
    status_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("wrote %s_summary.csv / equity.png under %s", spec.name, REPORTS_DIR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
