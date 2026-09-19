import datetime as dt

import pandas as pd

from notify.data import _flatten_columns, is_fresh_today


def test_flatten_multiindex_takes_price_level():
    idx = pd.date_range("2024-01-01", periods=3)
    cols = pd.MultiIndex.from_product([["Open", "Close"], ["AAA"]])
    df = pd.DataFrame([[1, 2], [3, 4], [5, 6]], index=idx, columns=cols)
    out = _flatten_columns(df)
    assert list(out.columns) == ["Open", "Close"]


def test_flatten_single_level_noop():
    df = pd.DataFrame({"open": [1], "close": [2]})
    assert list(_flatten_columns(df).columns) == ["open", "close"]


def test_is_fresh_true_for_recent():
    idx = pd.date_range(end=dt.date.today(), periods=5)
    df = pd.DataFrame({"close": range(5)}, index=idx)
    assert is_fresh_today(df, "tw") is True


def test_is_fresh_false_for_stale():
    old = dt.date.today() - dt.timedelta(days=30)
    idx = pd.date_range(end=old, periods=5)
    df = pd.DataFrame({"close": range(5)}, index=idx)
    assert is_fresh_today(df, "tw") is False
