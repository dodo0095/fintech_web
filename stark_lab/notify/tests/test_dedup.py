import datetime as dt

import pytest
from django.utils import timezone

from notify.indicators import Signal
from notify.models import SignalLog, WatchTarget
from notify.runner import _recently_pushed


@pytest.fixture
def target(db):
    return WatchTarget.objects.create(
        symbol="TEST.TW", display_name="測試", asset_class="tw_stock", market="tw"
    )


def _log(target, when):
    SignalLog.objects.create(
        target=target,
        indicator="ma",
        direction="bullish",
        trigger_date=dt.date.today(),
        triggered_at=when,
        detail="x",
    )


def test_recently_pushed_within_24h(target):
    _log(target, timezone.now() - dt.timedelta(hours=2))
    assert _recently_pushed(target, Signal("ma", "bullish", "")) is True


def test_not_recently_pushed_after_24h(target):
    _log(target, timezone.now() - dt.timedelta(hours=25))
    assert _recently_pushed(target, Signal("ma", "bullish", "")) is False


def test_different_direction_not_deduped(target):
    _log(target, timezone.now() - dt.timedelta(hours=1))
    assert _recently_pushed(target, Signal("ma", "bearish", "")) is False
