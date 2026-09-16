"""本益比河流圖 valuation.py 單元測試（純 pytest，不依賴 Django / 網路）。

聚焦 6426 統新類「由虧轉盈 + 缺季」個股導致分帶線爆表的修正：
  #2 不跨零內插、#3 分位數定帶線、#4 缺季/由虧轉盈降級近似。

執行：python -m pytest news/test_valuation.py -q
"""
from __future__ import annotations

import pandas as pd
import pytest

from news.fetchers import valuation as v


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _series(vals, quarters):
    return pd.Series(list(vals), index=[pd.Timestamp(q) for q in quarters])


def _close_df(start="2023-01-01", periods=700, base=50.0, slope=0.03):
    idx = pd.bdate_range(start=start, periods=periods)
    closes = [base + slope * i for i in range(periods)]
    return pd.DataFrame({"Close": closes}, index=idx)


def _income_df(pairs, row_name="Diluted EPS"):
    """pairs: [(quarter_str, eps), ...] → DataFrame(index=[row], columns=quarters)."""
    cols = [pd.Timestamp(q) for q, _ in pairs]
    vals = [x for _, x in pairs]
    return pd.DataFrame([vals], index=[row_name], columns=cols)


class _FakeTicker:
    def __init__(self, hist, income=None, info=None):
        self._hist = hist
        self.quarterly_income_stmt = income if income is not None else pd.DataFrame()
        self.quarterly_financials = pd.DataFrame()
        self.quarterly_incomestmt = pd.DataFrame()
        self.quarterly_balance_sheet = pd.DataFrame()
        self.quarterly_balancesheet = pd.DataFrame()
        self._info = info or {}

    def history(self, period=None, auto_adjust=False):
        return self._hist

    def get_info(self):
        return self._info


_Q_CONT = ["2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31"]
_Q_GAP = ["2025-03-31", "2025-06-30", "2025-12-31", "2026-03-31"]  # 跳 2025-09


# --------------------------------------------------------------------------- #
# #2 不跨零內插
# --------------------------------------------------------------------------- #
def test_interp_cross_zero_marks_none():
    t0 = pd.Timestamp("2026-01-01").value
    t1 = pd.Timestamp("2026-04-01").value
    dates = ["2025-06-01", "2026-02-15", "2026-06-01"]  # 左界外 / 跨零段 / 右界外
    out = v._interp_to_dates([(t0, -1.0), (t1, 3.0)], dates, no_cross_zero=True)
    assert out[0] == -1.0          # clamp 到左錨點（負）
    assert out[1] is None          # 負→正跨零段 → None，不製造貼零假分母
    assert out[2] == 3.0           # clamp 到右錨點（正）


def test_interp_too_few_points_returns_none():
    assert v._interp_to_dates([(1, 2.0)], ["2026-01-01"], no_cross_zero=True) is None


def test_interp_without_flag_still_crosses_zero():
    t0 = pd.Timestamp("2026-01-01").value
    t1 = pd.Timestamp("2026-04-01").value
    out = v._interp_to_dates([(t0, -1.0), (t1, 3.0)], ["2026-02-15"], no_cross_zero=False)
    assert out[0] is not None      # 舊行為：照樣內插穿過零


def test_ttm_eps_cross_zero_segment_is_none():
    quarters = [
        "2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31",
        "2026-03-31", "2026-06-30", "2026-09-30",
    ]
    eps_q = _series([-3, -3, -3, 4, 4, 4, 4], quarters)
    # TTM 錨點：2025-12=-5、2026-03=+2（跨零）；此日期落在兩者之間 → None
    out = v._ttm_eps_for_dates(eps_q, ["2026-02-01"])
    assert out == [None]


# --------------------------------------------------------------------------- #
# #3 分位數定帶線
# --------------------------------------------------------------------------- #
def test_percentile_matches_numpy_default():
    vals = [float(x) for x in range(1, 101)]
    assert v._percentile(vals, 50) == pytest.approx(50.5)
    assert v._percentile(vals, 5) == pytest.approx(5.95)
    assert v._percentile(vals, 95) == pytest.approx(95.05)


def test_percentile_excludes_outliers():
    vals = sorted([10.0] * 99 + [100000.0])
    assert v._percentile(vals, 95) < 100      # 離群值被排除
    assert v._percentile(vals, 5) == 10.0


def test_build_bands_percentile_caps_outlier():
    per = [1.0] * 100
    closes = [10.0] * 99 + [1000.0]           # 一個爆表離群比值
    band = v.build_bands(closes, per, "本益比")
    assert band is not None
    assert band["lines"][-1] < 50             # 上緣由 P95 決定，不被 1000 撐爆


def test_build_bands_insufficient_ratio_returns_none():
    # 有效正比值 < 30 → 資料不足，不畫帶線
    assert v.build_bands([10.0] * 10, [1.0] * 10, "本益比") is None


def test_build_bands_current_skips_trailing_none():
    per = [2.0] * 40 + [None, None]           # 最後兩天落在跨零段（None）
    closes = [80.0] * 42
    band = v.build_bands(closes, per, "本益比")
    assert band["current"] == 40.0            # 取最後一個有效正值 80/2，而非 None


# --------------------------------------------------------------------------- #
# #4 缺季 / 由虧轉盈 判定
# --------------------------------------------------------------------------- #
def test_max_consecutive_quarters():
    assert v._max_consecutive_quarters(_series([1, 1, 1, 1], _Q_CONT)) == 4
    assert v._max_consecutive_quarters(_series([1, 1, 1, 1], _Q_GAP)) == 2


def test_quarterly_series_usable():
    assert v._quarterly_series_usable(_series([1, 2, 3, 4], _Q_CONT)) is True
    assert v._quarterly_series_usable(_series([-1, 2, 3, 4], _Q_CONT)) is False  # 有負季
    assert v._quarterly_series_usable(_series([1, 2, 3, 4], _Q_GAP)) is False    # 缺季 <4 連續
    assert v._quarterly_series_usable(None) is False


def test_ttm_unusable():
    assert v._ttm_unusable(None) is True
    assert v._ttm_unusable([]) is True
    assert v._ttm_unusable([None, -1.0, 0.0]) is True
    assert v._ttm_unusable([None, 2.0]) is False


def test_trailing_eps_const_variants():
    class _GetInfo:
        def get_info(self):
            return {"trailingEps": 3.96}

    class _DotInfo:
        info = {"trailingEps": "n/a"}

    assert v._trailing_eps_const(_GetInfo()) == 3.96
    assert v._trailing_eps_const(_DotInfo()) is None


# --------------------------------------------------------------------------- #
# build_symbol 整合：由虧轉盈+缺季 → 降級近似且帶線不爆表；健康股 → 走 TTM
# --------------------------------------------------------------------------- #
def test_build_symbol_turnaround_degrades_to_approx(monkeypatch):
    import yfinance

    hist = _close_df(base=50.0, slope=0.02)
    # 含負值 + 缺季（跳 2024-12）：模擬 6426 統新型態
    income = _income_df([
        ("2024-06-30", -1.0),
        ("2024-09-30", -0.5),
        ("2025-06-30", 0.3),
        ("2025-09-30", 0.4),
        ("2025-12-31", 0.5),
        ("2026-03-31", 0.6),
        ("2026-06-30", 2.0),
    ])
    fake = _FakeTicker(hist, income, info={"trailingEps": 2.0, "sharesOutstanding": 1e8})
    monkeypatch.setattr(yfinance, "Ticker", lambda _s: fake)

    payload = v.build_symbol("9999.TW", "測試")
    assert payload is not None
    assert payload["approximate"] is True          # (c) 缺季/由虧轉盈 → 近似降級
    upper = payload["pe_lines"][-1]
    assert upper < 100                             # (b) 上緣落在合理上限，不破百倍離群
    assert payload["pe_lines"] == sorted(payload["pe_lines"])


def test_build_symbol_healthy_uses_ttm(monkeypatch):
    import yfinance

    hist = _close_df(base=50.0, slope=0.03)
    income = _income_df([
        ("2023-06-30", 1.0), ("2023-09-30", 1.1), ("2023-12-31", 1.2),
        ("2024-03-31", 1.3), ("2024-06-30", 1.4), ("2024-09-30", 1.5),
        ("2024-12-31", 1.6), ("2025-03-31", 1.7), ("2025-06-30", 1.8),
        ("2025-09-30", 1.9), ("2025-12-31", 2.0),
    ])
    fake = _FakeTicker(hist, income, info={"trailingEps": 7.0})
    monkeypatch.setattr(yfinance, "Ticker", lambda _s: fake)

    payload = v.build_symbol("8888.TW", "健康")
    assert payload is not None
    assert payload["approximate"] is False         # 連續正季 → 走 TTM 河流圖
    lines = payload["pe_lines"]
    assert lines == sorted(lines)                  # 遞增
    assert lines[-1] < 300                         # 合理範圍
