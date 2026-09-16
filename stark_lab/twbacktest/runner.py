"""Locate snr_backtest, spawn its venv python, parse reports/. No live trading."""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from dataclasses import asdict, fields, is_dataclass
from pathlib import Path

FALLBACK_STRATEGIES = (
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

# kept for older imports
ALLOWED_STRATEGIES = FALLBACK_STRATEGIES

STRATEGY_LABELS = {
    "breakout_v1": "突破 v1（SNR 閘）",
    "breakout_v2": "突破 v2（大盤濾網＋移動停利）",
    "breakout_raw": "突破 raw（無 SNR 閘）",
    "pullback_v1": "拉回 v1（SNR 閘）",
    "pullback_raw": "拉回 raw（無 SNR 閘）",
    "macd_v1": "MACD v1（SNR 閘）",
    "macd_v2": "MACD v2",
    "macd_raw": "MACD raw（無 SNR 閘）",
    "rsi_v1": "RSI v1（SNR 閘）",
    "rsi_v2": "RSI v2",
    "rsi_raw": "RSI raw（無 SNR 閘）",
    "kd_v1": "KD v1（SNR 閘）",
    "kd_v2": "KD v2",
    "kd_raw": "KD raw（無 SNR 閘）",
    "sma_v1": "均線 v1（SNR 閘）",
    "sma_v2": "均線 v2",
    "sma_raw": "均線 raw（無 SNR 閘）",
    "bb_v1": "布林 v1（SNR 閘）",
    "bb_v2": "布林 v2",
    "bb_raw": "布林 raw（無 SNR 閘）",
}

MVP_STRATEGIES = FALLBACK_STRATEGIES

PARAM_LABELS = {
    "tp": "停利（小數，0.25＝+25%）",
    "sl": "停損（小數，0.20＝-20%）",
    "time_stop_days": "時間停損天數（0＝關閉）",
    "lookback": "回看天數",
    "use_snr": "啟用 SNR 閘",
    "snr_min": "SNR 下限",
    "snr_max": "SNR 上限",
    "twii_filter": "大盤濾網（TWII＞SMA）",
    "trail": "移動停利",
    "trail_arm": "移動停利啟動（小數，0.12＝+12%）",
    "trail_lookback": "移動停利回看天數",
    "vol_mult": "量能倍數（0＝關閉）",
    "no_chase": "不追價",
    "chase_mult": "追價倍數",
    "snr_rising": "SNR 需上升",
}

GROUP_DEFS = (
    ("risk", "進出與風控", ("tp", "sl", "time_stop_days", "lookback")),
    ("snr", "SNR 閘", ("use_snr", "snr_min", "snr_max")),
    ("v2", "突破 v2 濾網／移動停利", (
        "twii_filter", "trail", "trail_arm", "trail_lookback",
        "vol_mult", "no_chase", "chase_mult", "snr_rising",
    )),
    ("sma", "均線", ()),
    ("band", "通道／帶寬", ()),
    ("macd", "MACD", ()),
    ("rsi", "RSI", ()),
    ("kd", "KD", ()),
    ("bb", "布林通道", ()),
    ("other", "其他參數", ()),
)

PREFIX_GROUP = (
    ("sma_", "sma"),
    ("band_", "band"),
    ("macd_", "macd"),
    ("rsi_", "rsi"),
    ("kd_", "kd"),
    ("bb_", "bb"),
)

SKIP_FIELDS = {"name", "kind"}

# Only these keys are shown / submitted for each strategy (keeps the form tidy).
_V2_EXTRA = (
    "snr_min", "snr_rising", "vol_mult", "twii_filter",
    "no_chase", "chase_mult", "trail", "trail_arm", "trail_lookback",
)


def relevant_keys(name: str, kind: str, payload: dict | None = None) -> list[str]:
    """Editable fields that matter for this strategy id / kind."""
    payload = payload or {}
    risk = ["tp", "sl", "time_stop_days"]
    use_snr = bool(payload.get("use_snr"))
    kind = (kind or _kind_from_name(name) or "").lower()
    name_l = (name or "").lower()

    if "v2" in name_l and kind == "breakout":
        return risk + ["lookback", "use_snr"] + list(_V2_EXTRA)
    if kind == "breakout":
        keys = risk + ["lookback", "use_snr"]
        if use_snr:
            keys.append("snr_min")
        return keys
    if kind == "pullback":
        keys = risk + ["lookback", "use_snr", "sma_fast", "sma_trend"]
        if use_snr:
            keys.append("snr_max")
        return keys
    if kind == "macd":
        return risk + ["macd_fast", "macd_slow", "macd_signal"]
    if kind == "rsi":
        return risk + ["rsi_n", "rsi_os", "rsi_ob"]
    if kind == "kd":
        return risk + ["kd_n", "kd_k", "kd_d", "kd_os", "kd_ob"]
    if kind == "sma":
        keys = risk + ["sma_fast", "sma_trend"]
        if "sma_slow" in payload:
            keys.append("sma_slow")
        return keys
    if kind == "bb":
        return risk + ["bb_n", "bb_k", "bb_mode"]
    # unknown: keep whatever we have except skipped
    return risk + [k for k in payload if k not in SKIP_FIELDS]


def filter_strategy_defaults(name: str, kind: str, payload: dict) -> dict:
    keys = relevant_keys(name, kind, payload)
    out = {}
    for k in keys:
        if k in payload:
            out[k] = payload[k]
        elif k == "lookback":
            out[k] = 20
        elif k in ("sma_fast",):
            out[k] = 20
        elif k in ("sma_trend",):
            out[k] = 60
    return out


FALLBACK_TICKERS = {
    "2330.TW": "台積電",
    "3035.TW": "致新",
    "5314.TWO": "世紀",
    "6197.TW": "佳必琪",
    "6217.TWO": "中探針",
    "2360.TW": "致茂電子",
    "2404.TW": "漢唐",
    "3037.TW": "欣興電子",
    "2449.TW": "京元電子",
    "3044.TW": "健鼎科技",
}

DEFAULT_ROOTS = (
    Path(r"C:\Users\AUSER\Desktop\trade\snr_backtest"),
    Path(r"C:/Users/AUSER/Desktop/trade/snr_backtest"),
    Path("/workspace/trade"),
)

DEFAULT_TIMEOUT = 300


def _django_setting(name: str, default=None):
    try:
        from django.conf import settings

        return getattr(settings, name, default)
    except Exception:
        return default


def backtest_root() -> Path:
    override = _django_setting("BACKTEST_ROOT") or os.environ.get("BACKTEST_ROOT")
    candidates = []
    if override:
        candidates.append(Path(override))
    candidates.extend(DEFAULT_ROOTS)
    for p in candidates:
        p = Path(p).expanduser()
        if (p / "run.py").exists() and (p / "engine.py").exists():
            return p.resolve()
    raise FileNotFoundError(
        "找不到 snr_backtest（需要 run.py 與 engine.py）。"
        "請在 Django settings 設 BACKTEST_ROOT，或確認 Desktop\\trade\\snr_backtest。"
    )


def reports_dir(root: Path | None = None) -> Path:
    root = root or backtest_root()
    return root / "reports"


def backtest_python(root: Path | None = None) -> Path:
    root = root or backtest_root()
    win = root / ".venv" / "Scripts" / "python.exe"
    nix = root / ".venv" / "bin" / "python"
    if win.exists():
        return win
    if nix.exists():
        return nix
    return Path(sys.executable)


def cli_path() -> Path:
    return Path(__file__).resolve().parent / "cli.py"


def defaults_json_path() -> Path:
    return Path(__file__).resolve().parent / "_defaults.json"


def load_defaults_json() -> dict:
    """tickers + per-strategy StrategySpec-ish fields exported for the web UI."""
    p = defaults_json_path()
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}



def last_run_path(root: Path | None = None) -> Path:
    return reports_dir(root) / "_web_last_run.json"


def read_last_run(root: Path | None = None) -> dict:
    p = last_run_path(root)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _fmt_pct(val) -> str:
    try:
        if val is None or val == "":
            return "n/a"
        x = float(val)
        if x != x:
            return "n/a"
        return f"{x * 100:.1f}%"
    except (TypeError, ValueError):
        return "n/a"


def _fmt_num(val, nd=2) -> str:
    try:
        if val is None or val == "":
            return "n/a"
        x = float(val)
        if x != x:
            return "n/a"
        if abs(x) == float("inf"):
            return "inf"
        return f"{x:.{nd}f}"
    except (TypeError, ValueError):
        return "n/a"


def _fmt_int(val) -> str:
    try:
        if val is None or val == "":
            return "n/a"
        return str(int(float(val)))
    except (TypeError, ValueError):
        return "n/a"


def _fmt_money(val) -> str:
    try:
        if val is None or val == "":
            return "n/a"
        return f"{float(val):,.0f}"
    except (TypeError, ValueError):
        return "n/a"


METRIC_SPECS = (
    ("trades", "成交筆數", _fmt_int),
    ("win_rate", "勝率", _fmt_pct),
    ("expectancy", "期望值／筆", _fmt_pct),
    ("total_return", "總報酬", _fmt_pct),
    ("max_drawdown", "最大回撤", _fmt_pct),
    ("cagr", "CAGR", _fmt_pct),
    ("profit_factor", "獲利因子", _fmt_num),
    ("final_equity", "最終權益（合計）", _fmt_money),
)


def parse_summary_csv(path: Path) -> tuple[dict, list[dict]]:
    """Return (equal_weight_row, per_ticker_rows)."""
    if not path.exists():
        return {}, []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    ew: dict = {}
    names: list[dict] = []
    skip = {"EQUAL_WEIGHT", "EQUAL_WEIGHT_NO_5314"}
    for row in rows:
        ticker = (row.get("ticker") or "").strip()
        if ticker == "EQUAL_WEIGHT":
            ew = row
        elif ticker not in skip:
            names.append(row)
    return ew, names


def metrics_for_display(row: dict) -> list[dict]:
    out = []
    for key, label, fmt in METRIC_SPECS:
        out.append({"key": key, "label": label, "value": fmt(row.get(key))})
    return out


def strategy_label(name: str) -> str:
    if name in STRATEGY_LABELS:
        return STRATEGY_LABELS[name]
    kind, _, suffix = name.partition("_")
    kind_zh = {
        "breakout": "突破",
        "pullback": "拉回",
        "macd": "MACD",
        "rsi": "RSI",
        "kd": "KD",
        "sma": "均線",
        "bb": "布林",
    }.get(kind, kind)
    extra = {"v1": "v1", "v2": "v2", "raw": "raw（無 SNR 閘）"}.get(suffix, suffix)
    return f"{kind_zh} {extra}".strip()


def _jsonable(v):
    if isinstance(v, bool) or v is None:
        return v
    if isinstance(v, int) and not isinstance(v, bool):
        return v
    if isinstance(v, float):
        if v != v or abs(v) == float("inf"):
            return None
        return v
    if isinstance(v, str):
        return v
    try:
        if hasattr(v, "item"):
            return _jsonable(v.item())
    except Exception:
        pass
    return str(v)


def _field_type_name(ann) -> str:
    text = str(ann)
    origin = getattr(ann, "__origin__", None)
    args = getattr(ann, "__args__", ())
    types = []
    if origin is None:
        types = [ann]
    else:
        types = [a for a in args if a is not type(None)]
    if bool in types and int not in types:
        return "bool"
    if int in types and float not in types:
        return "int"
    if float in types:
        return "float"
    if str in types:
        return "str"
    low = text.lower()
    if "bool" in low:
        return "bool"
    if "int" in low and "float" not in low:
        return "int"
    if "float" in low:
        return "float"
    return "str"


def _group_for(name: str) -> str:
    named = {
        "tp": "risk", "sl": "risk", "time_stop_days": "risk", "lookback": "risk",
        "use_snr": "snr", "snr_min": "snr", "snr_max": "snr",
        "twii_filter": "v2", "trail": "v2", "trail_arm": "v2", "trail_lookback": "v2",
        "vol_mult": "v2", "no_chase": "v2", "chase_mult": "v2", "snr_rising": "v2",
    }
    if name in named:
        return named[name]
    for prefix, gid in PREFIX_GROUP:
        if name.startswith(prefix):
            return gid
    return "other"


def _pretty_field(name: str) -> str:
    if name in PARAM_LABELS:
        return PARAM_LABELS[name]
    prefix_zh = {
        "sma_": "均線 ",
        "band_": "通道 ",
        "macd_": "MACD ",
        "rsi_": "RSI ",
        "kd_": "KD ",
        "bb_": "布林 ",
        "snr_": "SNR ",
        "trail_": "移動停利 ",
    }
    for prefix, zh in prefix_zh.items():
        if name.startswith(prefix):
            rest = name[len(prefix):]
            return zh + rest
    return name


def _with_root_on_path(root: Path):
    root_s = str(root)
    inserted = False
    if root_s not in sys.path:
        sys.path.insert(0, root_s)
        inserted = True
    dropped = []
    for name in ("config", "strategies", "engine", "data", "run", "universe"):
        if name in sys.modules:
            dropped.append((name, sys.modules.pop(name)))
    try:
        yield  # type: ignore
    finally:
        if inserted and sys.path and sys.path[0] == root_s:
            sys.path.pop(0)
        for name, _old in dropped:
            sys.modules.pop(name, None)


class _PathCM:
    def __init__(self, root: Path):
        self.root = str(root)
        self.inserted = False
        self.dropped = []

    def __enter__(self):
        if self.root not in sys.path:
            sys.path.insert(0, self.root)
            self.inserted = True
        for name in ("config", "strategies", "engine", "data", "run", "universe"):
            if name in sys.modules:
                self.dropped.append(name)
                sys.modules.pop(name, None)
        return self

    def __exit__(self, *exc):
        if self.inserted and sys.path and sys.path[0] == self.root:
            sys.path.pop(0)
        for name in ("config", "strategies", "engine", "data", "run", "universe"):
            sys.modules.pop(name, None)
        return False


def _iter_specs():
    import strategies as st

    specs = []
    if hasattr(st, "all_strategies"):
        try:
            specs.extend(list(st.all_strategies() or []))
        except Exception:
            pass
    for attr in dir(st):
        if not attr.startswith("make_"):
            continue
        fn = getattr(st, attr)
        if not callable(fn):
            continue
        try:
            spec = fn()
        except TypeError:
            continue
        except Exception:
            continue
        if spec is not None and getattr(spec, "name", None):
            specs.append(spec)
    seen = set()
    out = []
    for spec in specs:
        n = spec.name
        if n in seen:
            continue
        seen.add(n)
        out.append(spec)
    return out


def load_universe_meta(root: Path | None = None) -> dict:
    """Read TICKERS + StrategySpec defaults from snr_backtest (this run only)."""
    try:
        root = root or backtest_root()
    except FileNotFoundError as exc:
        return {
            "ok": False,
            "error": str(exc),
            "tickers": dict(FALLBACK_TICKERS),
            "tickers_text": tickers_to_text(FALLBACK_TICKERS),
            "strategies": [],
            "defaults": {},
            "param_groups": [],
        }

    tickers = dict(FALLBACK_TICKERS)
    defaults: dict[str, dict] = {}
    kinds: dict[str, str] = {}
    field_meta: dict[str, dict] = {}
    order: list[str] = []

    try:
        with _PathCM(root):
            try:
                from config import TICKERS as CFG_TICKERS  # type: ignore

                if isinstance(CFG_TICKERS, dict) and CFG_TICKERS:
                    tickers = {str(k): str(v) for k, v in CFG_TICKERS.items()}
            except Exception:
                pass
            try:
                specs = _iter_specs()
            except Exception:
                specs = []
            for spec in specs:
                if not is_dataclass(spec):
                    continue
                name = spec.name
                order.append(name)
                raw = asdict(spec)
                kinds[name] = str(raw.get("kind") or _kind_from_name(name))
                payload = {}
                for f in fields(spec):
                    if f.name in SKIP_FIELDS:
                        continue
                    payload[f.name] = _jsonable(raw.get(f.name))
                    field_meta.setdefault(
                        f.name,
                        {
                            "name": f.name,
                            "type": _field_type_name(f.type),
                            "group": _group_for(f.name),
                            "label": _pretty_field(f.name),
                        },
                    )
                defaults[name] = payload
    except Exception:
        pass

    if not order:
        order = list(FALLBACK_STRATEGIES)
        for name in order:
            kinds[name] = _kind_from_name(name)
            defaults.setdefault(name, {})

    # Prefer exported _defaults.json (tickers + per-strategy fields) when present.
    exported = load_defaults_json()
    if exported:
        exp_tickers = exported.get("tickers")
        if isinstance(exp_tickers, dict) and exp_tickers:
            tickers = {str(k): str(v) for k, v in exp_tickers.items()}
        exp_strats = exported.get("strategies") or {}
        if isinstance(exp_strats, dict):
            for name, payload in exp_strats.items():
                if not isinstance(payload, dict):
                    continue
                if name not in order:
                    order.append(name)
                kinds.setdefault(name, str(payload.get("kind") or _kind_from_name(name)))
                base = dict(defaults.get(name) or {})
                for k, v in payload.items():
                    if k in SKIP_FIELDS:
                        continue
                    base[k] = _jsonable(v)
                    field_meta.setdefault(
                        k,
                        {
                            "name": k,
                            "type": (
                                "bool" if isinstance(v, bool)
                                else "int" if isinstance(v, int) and not isinstance(v, bool)
                                else "float" if isinstance(v, (int, float)) or v is None
                                else "str"
                            ),
                            "group": _group_for(k),
                            "label": _pretty_field(k),
                        },
                    )
                defaults[name] = base

    # Ensure common editable keys exist in the form even if a spec omits them.
    for extra_name, extra_type in (
        ("tp", "float"),
        ("sl", "float"),
        ("time_stop_days", "int"),
        ("lookback", "int"),
        ("use_snr", "bool"),
        ("snr_min", "float"),
        ("snr_max", "float"),
        ("twii_filter", "bool"),
        ("trail", "bool"),
        ("trail_arm", "float"),
        ("trail_lookback", "int"),
        ("vol_mult", "float"),
        ("no_chase", "bool"),
        ("chase_mult", "float"),
        ("snr_rising", "bool"),
    ):
        field_meta.setdefault(
            extra_name,
            {
                "name": extra_name,
                "type": extra_type,
                "group": _group_for(extra_name),
                "label": _pretty_field(extra_name),
            },
        )

    # Drop irrelevant keys so the UI only shows this strategy's knobs.
    for name in list(defaults.keys()):
        kind = kinds.get(name) or _kind_from_name(name)
        defaults[name] = filter_strategy_defaults(name, kind, defaults.get(name) or {})

    groups = []
    grouped_names = set()
    for gid, glabel, fixed in GROUP_DEFS:
        names = list(fixed)
        for fname, meta in field_meta.items():
            if meta["group"] == gid and fname not in names:
                names.append(fname)
        fields_out = [field_meta[n] for n in names if n in field_meta]
        if not fields_out and gid not in {"risk", "snr", "v2"}:
            continue
        grouped_names.update(n["name"] for n in fields_out)
        groups.append({"id": gid, "label": glabel, "fields": fields_out})

    strategies = []
    for name in order:
        strategies.append({
            "id": name,
            "label": strategy_label(name),
            "kind": kinds.get(name) or _kind_from_name(name),
        })

    return {
        "ok": True,
        "tickers": tickers,
        "tickers_text": tickers_to_text(tickers),
        "strategies": strategies,
        "defaults": defaults,
        "param_groups": groups,
        "allowed": [s["id"] for s in strategies],
    }


def _kind_from_name(name: str) -> str:
    return (name or "").split("_", 1)[0] or "breakout"


def tickers_to_text(tickers: dict) -> str:
    lines = []
    for code, name in tickers.items():
        code = str(code).strip()
        name = str(name).strip()
        if not code:
            continue
        if name and name != code:
            lines.append(f"{code} {name}")
        else:
            lines.append(code)
    return "\n".join(lines)


def parse_tickers_text(text: str) -> dict[str, str]:
    """Parse textarea: one ticker per line, `code` or `code name`."""
    import re

    out: dict[str, str] = {}
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "," in line and " " not in line.split(",", 1)[0]:
            parts = [p.strip() for p in line.split(",", 1)]
        else:
            parts = re.split(r"[\s;]+", line, maxsplit=1)
        code = (parts[0] if parts else "").strip()
        name = (parts[1] if len(parts) > 1 else "").strip()
        if not code:
            continue
        up = code.upper()
        if re.fullmatch(r"\d{4}", up):
            up = up + ".TW"
        elif re.fullmatch(r"\d{4}TWO", up):
            up = up[:4] + ".TWO"
        out[up] = name or up
    return out


def allowed_strategy_ids(root: Path | None = None) -> tuple[str, ...]:
    meta = load_universe_meta(root)
    ids = tuple(meta.get("allowed") or [])
    return ids if ids else FALLBACK_STRATEGIES


def load_report(strategy: str, root: Path | None = None) -> dict:
    allowed = allowed_strategy_ids(root)
    if strategy not in allowed and strategy not in FALLBACK_STRATEGIES:
        return {"ok": False, "error": f"不支援的策略：{strategy}"}
    root = root or backtest_root()
    rd = reports_dir(root)
    summary_path = rd / f"{strategy}_summary.csv"
    png_path = rd / f"{strategy}_equity.png"
    ew, names = parse_summary_csv(summary_path)
    last = read_last_run(root)
    pretty = []
    for row in names:
        pretty.append({
            "ticker": row.get("ticker", ""),
            "name": row.get("name", ""),
            "trades": _fmt_int(row.get("trades")),
            "win_rate": _fmt_pct(row.get("win_rate")),
            "total_return": _fmt_pct(row.get("total_return")),
            "max_drawdown": _fmt_pct(row.get("max_drawdown")),
        })
    return {
        "ok": bool(ew) or png_path.exists(),
        "strategy": strategy,
        "label": strategy_label(strategy),
        "equal_weight": ew,
        "metrics": metrics_for_display(ew) if ew else [],
        "per_ticker": pretty,
        "has_chart": png_path.exists(),
        "summary_path": str(summary_path) if summary_path.exists() else "",
        "chart_path": str(png_path) if png_path.exists() else "",
        "last_run": last if last.get("strategy") == strategy else last,
        "reports_dir": str(rd),
    }


def run_strategy(
    strategy: str,
    start: str = "",
    end: str = "",
    timeout: int | None = None,
    root: Path | None = None,
    params: dict | None = None,
    tickers: dict | None = None,
    refresh: bool = True,
) -> dict:
    allowed = allowed_strategy_ids(root)
    if strategy not in allowed and strategy not in FALLBACK_STRATEGIES:
        return {"ok": False, "error": f"不支援的策略：{strategy}", "log": ""}
    root = root or backtest_root()
    py = backtest_python(root)
    cli = cli_path()
    if not cli.exists():
        return {"ok": False, "error": f"找不到 CLI：{cli}", "log": ""}
    timeout = timeout or int(_django_setting("BACKTEST_TIMEOUT", DEFAULT_TIMEOUT) or DEFAULT_TIMEOUT)
    cmd = [
        str(py),
        str(cli),
        "--root",
        str(root),
        "--strategy",
        strategy,
    ]
    if start:
        cmd += ["--start", start]
    if end:
        cmd += ["--end", end]
    if params:
        cmd += ["--params", json.dumps(params, ensure_ascii=False)]
    if tickers:
        cmd += ["--tickers", json.dumps(tickers, ensure_ascii=False)]

    # refresh on: omit flags → get_price auto-fills when cache short of end
    # refresh off: cache only (no Yahoo)
    if not refresh:
        cmd += ["--no-download"]

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        tail = ""
        if exc.stderr:
            tail = exc.stderr[-4000:] if isinstance(exc.stderr, str) else ""
        elif exc.stdout:
            tail = exc.stdout[-4000:] if isinstance(exc.stdout, str) else ""
        return {
            "ok": False,
            "error": f"回測逾時（{timeout} 秒）。可把 BACKTEST_TIMEOUT 調大，或先「只看既有報告」。",
            "log": tail,
            "returncode": -1,
        }
    except OSError as exc:
        return {"ok": False, "error": f"無法啟動回測 Python：{py}（{exc}）", "log": ""}

    log = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
    if proc.returncode != 0:
        return {
            "ok": False,
            "error": f"回測失敗（exit {proc.returncode}）。未改紙上帳戶。",
            "log": log[-8000:],
            "returncode": proc.returncode,
        }
    report = load_report(strategy, root)
    report["log"] = log[-8000:]
    report["ok"] = True
    return report
