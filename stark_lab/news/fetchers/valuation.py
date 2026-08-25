"""本益比(PE)/淨值比(PB) 河流圖 → valuation bundle（自 fetch_valuation.py 移植）。

build() 回傳：{
  "symbols": {code: payload, ...},   # 每檔 valuation_{code}.json 內容
  "default_code": code,              # 預設 valuation.json 對應的代碼
  "watchlist": [{code, symbol, name}, ...],
}
失敗（全部標的都算不出）則丟例外。
支援 STOCK_SYMBOL / STOCK_NAME 環境變數指定單一標的。
"""
from __future__ import annotations

import os

from .common import now_iso, safe_float

WATCHLIST = [
    ("2330.TW", "台積電"),
    ("2317.TW", "鴻海"),
    ("2454.TW", "聯發科"),
    ("2308.TW", "台達電"),
]

N_LINES = 6


def _get_price(t):
    for period in ("5y", "3y", "2y", "1y"):
        hist = t.history(period=period, auto_adjust=False)
        if hist is not None and not hist.empty:
            hist = hist.dropna(subset=["Close"])
            if len(hist) >= 60:
                dates, closes = [], []
                for idx, row in hist.iterrows():
                    try:
                        d = idx.tz_localize(None).strftime("%Y-%m-%d") if hasattr(idx, "tz_localize") else str(idx)[:10]
                    except Exception:
                        d = str(idx)[:10]
                    c = safe_float(row["Close"])
                    if c is None:
                        continue
                    dates.append(d)
                    closes.append(round(c, 4))
                return dates, closes
    return [], []


def _interp_to_dates(points, dates):
    try:
        import bisect
        import pandas as pd

        if len(points) < 2:
            return None
        points = sorted(points)
        xs = [p[0] for p in points]
        ys = [float(p[1]) for p in points]
        out = []
        for d in dates:
            tt = pd.Timestamp(d).value
            if tt <= xs[0]:
                out.append(ys[0])
            elif tt >= xs[-1]:
                out.append(ys[-1])
            else:
                j = bisect.bisect_right(xs, tt)
                x0, x1, y0, y1 = xs[j - 1], xs[j], ys[j - 1], ys[j]
                frac = (tt - x0) / (x1 - x0) if x1 > x0 else 0.0
                out.append(y0 + (y1 - y0) * frac)
        return out
    except Exception:
        return None


def _quarterly_eps(t):
    for attr in ("quarterly_income_stmt", "quarterly_financials", "quarterly_incomestmt"):
        df = getattr(t, attr, None)
        try:
            if df is None or getattr(df, "empty", True):
                continue
            rows = [i for i in df.index if isinstance(i, str) and "eps" in i.lower()]
            if not rows:
                continue
            row = None
            for pref in ("diluted eps", "basic eps"):
                for r in rows:
                    if pref in r.lower():
                        row = r
                        break
                if row:
                    break
            row = row or rows[0]
            s = df.loc[row].dropna().sort_index()
            if len(s) >= 4:
                return s
        except Exception:
            continue
    return None


def _derive_quarterly_eps(t):
    try:
        import pandas as pd

        df = None
        for attr in ("quarterly_income_stmt", "quarterly_financials", "quarterly_incomestmt"):
            d = getattr(t, attr, None)
            if d is not None and not getattr(d, "empty", True):
                df = d
                break
        if df is None:
            return None

        def find_row(names):
            idx = list(df.index)
            for n in names:
                for i in idx:
                    if isinstance(i, str) and n.lower() == i.lower():
                        return i
            for n in names:
                for i in idx:
                    if isinstance(i, str) and n.lower() in i.lower():
                        return i
            return None

        ni_row = find_row(["Net Income Common Stockholders", "Net Income", "Net Income Continuous Operations"])
        if ni_row is None:
            return None
        ni = df.loc[ni_row].dropna()

        shares = None
        try:
            info = t.get_info() if hasattr(t, "get_info") else t.info
            shares = safe_float(info.get("sharesOutstanding"))
        except Exception:
            shares = None
        if not shares or shares <= 0:
            return None

        data = {}
        for col in ni.index:
            v = safe_float(ni[col])
            if v is not None:
                data[col] = v / shares
        if len(data) < 4:
            return None
        return pd.Series(data).sort_index()
    except Exception:
        return None


def _ttm_eps_for_dates(eps_q, dates):
    try:
        import pandas as pd

        eps_q = eps_q.astype(float).sort_index()
        ttm = eps_q.rolling(4).sum().dropna()
        if ttm.empty:
            return None
        pts = [(pd.Timestamp(str(x)[:10]).value, float(v)) for x, v in zip(ttm.index, ttm.values)]
        return _interp_to_dates(pts, dates)
    except Exception:
        return None


def _bvps_for_dates(t, dates):
    try:
        import pandas as pd

        bs = None
        for attr in ("quarterly_balance_sheet", "quarterly_balancesheet"):
            df = getattr(t, attr, None)
            if df is not None and not getattr(df, "empty", True):
                bs = df
                break
        if bs is None:
            return None

        def find_row(names):
            idx = list(bs.index)
            for n in names:
                for i in idx:
                    if isinstance(i, str) and n.lower() == i.lower():
                        return i
            for n in names:
                for i in idx:
                    if isinstance(i, str) and n.lower() in i.lower():
                        return i
            return None

        eq_row = find_row(["Common Stock Equity", "Stockholders Equity", "Total Stockholder Equity", "Total Equity Gross Minority Interest"])
        if eq_row is None:
            return None
        eq = bs.loc[eq_row].dropna()
        sh_row = find_row(["Ordinary Shares Number", "Share Issued", "Common Stock Shares Outstanding"])
        sh_series = bs.loc[sh_row].dropna() if sh_row is not None else None

        shares_const = None
        try:
            info = t.get_info() if hasattr(t, "get_info") else t.info
            shares_const = safe_float(info.get("sharesOutstanding"))
        except Exception:
            shares_const = None

        pts = []
        for col in eq.index:
            e = safe_float(eq[col])
            if e is None:
                continue
            sh = None
            if sh_series is not None and col in sh_series.index:
                sh = safe_float(sh_series[col])
            if sh is None or sh <= 0:
                sh = shares_const
            if sh is None or sh <= 0:
                continue
            pts.append((pd.Timestamp(str(col)[:10]).value, e / sh))
        return _interp_to_dates(pts, dates)
    except Exception:
        return None


def build_bands(closes, per_share, unit):
    ratio = [c / p for c, p in zip(closes, per_share) if p and p > 0]
    if len(ratio) < 30:
        return None
    rs = sorted(ratio)
    r_min, r_max = rs[0], rs[-1]
    rng = r_max - r_min if r_max > r_min else max(r_max, 1.0)
    pad = rng * 0.05
    lo = max(r_min - pad, r_min * 0.85, 0.01)
    hi = r_max + pad
    lines = [round(lo + (hi - lo) * k / (N_LINES - 1), 2) for k in range(N_LINES)]
    band_prices = [[round(L * p, 2) if (p and p > 0) else None for p in per_share] for L in lines]

    last_c, last_p = closes[-1], per_share[-1]
    current = round(last_c / last_p, 4) if last_p and last_p > 0 else None
    band_idx = None
    zone = "區間內"
    if current is not None:
        if current >= lines[-1]:
            band_idx = N_LINES - 2
        elif current <= lines[0]:
            band_idx = 0
        else:
            for k in range(N_LINES - 1):
                if lines[k] <= current <= lines[k + 1]:
                    band_idx = k
                    break
        top = N_LINES - 2
        if band_idx >= top:
            zone = "{} 5 年高點".format(unit)
        elif band_idx == 0:
            zone = "{} 5 年低點".format(unit)
        elif band_idx >= top - 1:
            zone = "{}偏高".format(unit)
        elif band_idx <= 1:
            zone = "{}偏低".format(unit)
        else:
            zone = "{}合理區".format(unit)
    return {"lines": lines, "band_prices": band_prices, "current": current, "current_band_index": band_idx, "zone_label": zone}


def build_symbol(symbol, name):
    import yfinance as yf

    print("  --- {} {} ---".format(symbol, name))
    t = yf.Ticker(symbol)
    dates, closes = _get_price(t)
    if len(closes) < 60:
        print("  [warn] {} 股價資料不足（{}）".format(symbol, len(closes)))
        return None

    pe_approx = False
    ttm_eps = None
    eps_q = _quarterly_eps(t)
    if eps_q is not None:
        ttm_eps = _ttm_eps_for_dates(eps_q, dates)
    if not ttm_eps or all(v is None or v <= 0 for v in ttm_eps):
        d_eps = _derive_quarterly_eps(t)
        if d_eps is not None:
            ttm_eps = _ttm_eps_for_dates(d_eps, dates)
    if not ttm_eps or all(v is None or v <= 0 for v in ttm_eps):
        eps_const = None
        try:
            info = t.get_info() if hasattr(t, "get_info") else t.info
            eps_const = safe_float(info.get("trailingEps"))
        except Exception:
            eps_const = None
        if eps_const and eps_const > 0:
            ttm_eps = [eps_const] * len(dates)
            pe_approx = True
        else:
            ttm_eps = None
    pe_block = build_bands(closes, ttm_eps, "本益比") if ttm_eps else None
    if pe_block is None:
        print("  [warn] {} 無法計算本益比，略過".format(symbol))
        return None

    bvps = _bvps_for_dates(t, dates)
    pb_block = build_bands(closes, bvps, "淨值比") if bvps else None

    last_close, last_eps = closes[-1], ttm_eps[-1]
    payload = {
        "symbol": symbol,
        "name": name,
        "updated_at": now_iso(),
        "dates": dates,
        "close": closes,
        "metric": "PE",
        "approximate": pe_approx,
        "current_close": round(last_close, 2),
        "current_eps": round(last_eps, 4) if last_eps else None,
        "current_pe": pe_block["current"],
        "current_band_index": pe_block["current_band_index"],
        "zone_label": pe_block["zone_label"],
        "pe_lines": pe_block["lines"],
        "band_prices": pe_block["band_prices"],
    }
    if pb_block:
        payload["pb"] = {
            "approximate": False,
            "current": pb_block["current"],
            "current_band_index": pb_block["current_band_index"],
            "zone_label": pb_block["zone_label"],
            "lines": pb_block["lines"],
            "band_prices": pb_block["band_prices"],
        }
    return payload


def build_symbol_try(code, name, preferred_yahoo=None):
    """Try .TW then .TWO (or TWO first if the listing file says 上櫃)."""
    from news.tickers import yahoo_candidates

    info = {"code": str(code or "").split(".")[0], "yahoo": preferred_yahoo or ""}
    last = None
    for symbol in yahoo_candidates(info):
        last = build_symbol(symbol, name or code)
        if last:
            return last
    return last


def build() -> dict:
    env_sym = os.environ.get("STOCK_SYMBOL")
    if env_sym:
        targets = [(env_sym, os.environ.get("STOCK_NAME", env_sym))]
    else:
        targets = WATCHLIST

    symbols = {}
    wl_items = []
    default_code = None
    for i, (symbol, name) in enumerate(targets):
        payload = build_symbol(symbol, name)
        if payload is None:
            continue
        code = symbol.split(".")[0]
        symbols[code] = payload
        wl_items.append({"code": code, "symbol": symbol, "name": name})
        if symbol.startswith("2330") or default_code is None:
            default_code = code

    if not symbols:
        raise RuntimeError("all valuation targets failed")

    return {
        "symbols": symbols,
        "default_code": default_code,
        "watchlist": {"updated_at": now_iso(), "items": wl_items},
    }
