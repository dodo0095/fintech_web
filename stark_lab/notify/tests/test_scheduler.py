import datetime as dt
from io import StringIO

import pytest
import pytz
from django.core.management import call_command

from notify.management.commands.run_scheduler import (
    _day_of_week,
    _parse_hhmm,
    _parse_times,
    build_scheduler,
)


def test_parse_hhmm_valid():
    assert _parse_hhmm("09:00") == (9, 0)
    assert _parse_hhmm("21:30") == (21, 30)


@pytest.mark.parametrize("bad", ["9", "25:00", "09:70", "abc", ""])
def test_parse_hhmm_invalid(bad):
    with pytest.raises(ValueError):
        _parse_hhmm(bad)


def test_parse_times_multiple():
    assert _parse_times("09:00,14:00") == [(9, 0), (14, 0)]
    assert _parse_times("21:00") == [(21, 0)]


def test_scheduler_disabled_does_not_start(settings):
    settings.SCHEDULER_ENABLED = False
    out = StringIO()
    call_command("run_scheduler", stdout=out)
    assert "未啟動" in out.getvalue()


def test_build_scheduler_single_time_per_market(settings):
    settings.SCHEDULE_TW = "09:00"
    settings.SCHEDULE_US = "21:00"
    scheduler = build_scheduler()
    ids = {job.id for job in scheduler.get_jobs()}
    assert ids == {"tw-0900", "us-2100"}


def test_build_scheduler_multiple_times_per_market(settings):
    settings.SCHEDULE_TW = "09:00,14:00"
    settings.SCHEDULE_US = "21:00,04:00"
    scheduler = build_scheduler()
    ids = {job.id for job in scheduler.get_jobs()}
    assert ids == {"tw-0900", "tw-1400", "us-2100", "us-0400"}


@pytest.mark.parametrize(
    ("market", "hour", "expected"),
    [
        ("tw", 9, "mon-fri"),
        ("tw", 14, "mon-fri"),
        ("us", 21, "mon-fri"),  # 美股盤前：預覽當日場次，週一~週五
        ("us", 4, "tue-sat"),  # 美股盤後清晨：前一交易日收盤，晚一天 → tue-sat
    ],
)
def test_day_of_week_per_slot(market, hour, expected):
    assert _day_of_week(market, hour) == expected


def test_us_post_close_slot_fires_on_saturday(settings):
    """美股 04:00 這一槽下一次觸發須落在台灣週六（對應美股週五收盤）。

    修正前用 mon-fri，從週五午後起算會跳到「週一 04:00」（漏掉週五美盤）；
    修正後為 tue-sat，會正確落在「週六 04:00」。
    """
    settings.SCHEDULE_US = "04:00"
    scheduler = build_scheduler()
    trigger = scheduler.get_job("us-0400").trigger
    tz = pytz.timezone(settings.TIME_ZONE)
    # 2026-07-31 是週五（隔日 08-01 為週六）
    friday_noon = tz.localize(dt.datetime(2026, 7, 31, 12, 0))
    nxt = trigger.get_next_fire_time(None, friday_noon)
    assert nxt.isoweekday() == 6  # 週六
    assert (nxt.hour, nxt.minute) == (4, 0)
