import datetime as dt

import pandas as pd
import pytest
from django.core.management import call_command

from notify import constants as C
from notify import runner
from notify.models import PushLog, SignalLog, WatchTarget


def _decreasing_df():
    idx = pd.date_range(end=dt.date.today(), periods=80)
    close = pd.Series(range(200, 120, -1), index=idx, dtype=float)  # RSI=0 → bullish
    return pd.DataFrame(
        {"open": close, "high": close + 1, "low": close - 1, "close": close, "volume": 0},
        index=idx,
    )


def _flat_df():
    idx = pd.date_range(end=dt.date.today(), periods=80)
    flat = pd.Series([100.0] * 80, index=idx)
    return pd.DataFrame(
        {"open": flat, "high": flat, "low": flat, "close": flat, "volume": 0}, index=idx
    )


@pytest.mark.django_db
def test_run_notify_dry_run_writes_logs_without_network(monkeypatch, settings):
    settings.DRY_RUN = True
    monkeypatch.setattr(runner.data, "fetch_daily", lambda symbol, days: _decreasing_df())
    monkeypatch.setattr(runner.data, "is_fresh_today", lambda df, market: True)

    def _boom(*a, **k):
        raise AssertionError("DRY_RUN 不應呼叫真實 Discord API")

    monkeypatch.setattr(runner.discord_client.requests, "post", _boom)

    call_command("run_notify", "--market", "tw")

    assert PushLog.objects.count() == 1
    pl = PushLog.objects.first()
    assert pl.channel == "discord"
    assert pl.status == "dry_run"
    assert pl.signal_count >= 1
    assert SignalLog.objects.filter(indicator="rsi", direction="bullish").exists()


@pytest.mark.django_db
def test_no_signal_still_pushes_price_block(monkeypatch, settings):
    """到點必推：即使 0 訊號，仍送出含價格區塊的訊息。"""
    settings.DRY_RUN = True
    monkeypatch.setattr(runner.data, "fetch_daily", lambda symbol, days: _flat_df())
    monkeypatch.setattr(runner.data, "is_fresh_today", lambda df, market: True)

    call_command("run_notify", "--market", "tw")

    pl = PushLog.objects.first()
    assert pl.signal_count == 0
    assert pl.push_mode != "none"  # 不再有「不推」路徑
    assert C.PRICE_HEADER in pl.message
    assert C.DISCLAIMER in pl.message


@pytest.mark.django_db
def test_all_targets_appear_in_price_block_every_run(monkeypatch, settings):
    """每個時點都掃全部標的：4 檔 seed 標的都要出現在價格區塊（不分 tw/us）。"""
    settings.DRY_RUN = True
    monkeypatch.setattr(runner.data, "fetch_daily", lambda symbol, days: _flat_df())
    monkeypatch.setattr(runner.data, "is_fresh_today", lambda df, market: True)

    call_command("run_notify", "--market", "tw")

    msg = PushLog.objects.first().message
    for name in [t["display_name"] for t in C.DEFAULT_TARGETS]:
        assert name in msg


@pytest.mark.django_db
def test_price_block_lists_target_even_when_fetch_fails(monkeypatch, settings):
    """抓取失敗的標的仍列在價格區塊，標註資料無法取得。"""
    settings.DRY_RUN = True

    def _fetch(symbol, days):
        if symbol == "GLD":
            raise runner.data.DataError("boom")
        return _flat_df()

    monkeypatch.setattr(runner.data, "fetch_daily", _fetch)
    monkeypatch.setattr(runner.data, "is_fresh_today", lambda df, market: True)

    call_command("run_notify", "--market", "us")

    msg = PushLog.objects.first().message
    assert "黃金(GLD)" in msg
    assert C.NOTE_NO_DATA in msg


@pytest.mark.django_db
def test_enabled_indicators_filters_out_disabled(monkeypatch, settings):
    """L0 全域開關：關閉 rsi 後，只會觸發 rsi 的資料應變成無訊號。"""
    settings.DRY_RUN = True
    settings.ENABLED_INDICATORS = ["ma", "macd"]  # 未含 rsi
    monkeypatch.setattr(runner.data, "fetch_daily", lambda symbol, days: _decreasing_df())
    monkeypatch.setattr(runner.data, "is_fresh_today", lambda df, market: True)

    call_command("run_notify", "--market", "tw")

    pl = PushLog.objects.first()
    assert pl.signal_count == 0
    assert not SignalLog.objects.filter(indicator="rsi").exists()
    # 訊號被關掉，但價格仍照推
    assert C.PRICE_HEADER in pl.message


@pytest.mark.django_db
def test_stale_target_still_shows_price_but_no_signal(monkeypatch, settings):
    """今日未開盤/資料過舊：不得用舊資料產生訊號，但價格仍照列並標註休市。"""
    settings.DRY_RUN = True
    monkeypatch.setattr(runner.data, "fetch_daily", lambda symbol, days: _decreasing_df())
    monkeypatch.setattr(runner.data, "is_fresh_today", lambda df, market: False)  # 全部視為過舊

    call_command("run_notify", "--market", "tw")

    assert SignalLog.objects.count() == 0
    pl = PushLog.objects.first()
    assert pl.signal_count == 0
    assert C.PRICE_HEADER in pl.message
    assert C.NOTE_STALE in pl.message


@pytest.mark.django_db
def test_run_notify_continues_when_one_target_fetch_fails(monkeypatch, settings):
    """單一標的抓取失敗（DataError）：略過該標的，其他標的續跑。"""
    settings.DRY_RUN = True
    WatchTarget.objects.create(symbol="FAIL.TW", display_name="FAIL", asset_class="tw_stock", market="tw")
    WatchTarget.objects.create(symbol="OK.TW", display_name="OK", asset_class="tw_stock", market="tw")

    def _fetch(symbol, days):
        if symbol == "FAIL.TW":
            raise runner.data.DataError("boom")
        return _decreasing_df()

    monkeypatch.setattr(runner.data, "fetch_daily", _fetch)
    monkeypatch.setattr(runner.data, "is_fresh_today", lambda df, market: True)

    call_command("run_notify", "--market", "tw")  # 不應拋出

    # 失敗標的沒有訊號，其他標的仍產生訊號並推播
    assert not SignalLog.objects.filter(target__symbol="FAIL.TW").exists()
    assert SignalLog.objects.filter(target__symbol="OK.TW").exists()
    assert PushLog.objects.first().signal_count >= 1


@pytest.mark.django_db
def test_us_market_appends_realtime_note_and_disclaimer(monkeypatch, settings):
    """美股時段訊息含『非即時』註記與免責聲明。"""
    settings.DRY_RUN = True
    monkeypatch.setattr(runner.data, "fetch_daily", lambda symbol, days: _decreasing_df())
    monkeypatch.setattr(runner.data, "is_fresh_today", lambda df, market: True)

    call_command("run_notify", "--market", "us")

    msg = PushLog.objects.first().message
    assert runner.US_NOTE in msg
    assert C.DISCLAIMER in msg


@pytest.mark.django_db
def test_no_signal_message_shows_no_signal_note_not_summary(monkeypatch, settings):
    """全數無訊號：訊息含『無訊號提示』，且不出現訊號摘要與門檻說明。"""
    settings.DRY_RUN = True
    monkeypatch.setattr(runner.data, "fetch_daily", lambda symbol, days: _flat_df())
    monkeypatch.setattr(runner.data, "is_fresh_today", lambda df, market: True)

    call_command("run_notify", "--market", "tw")

    msg = PushLog.objects.first().message
    assert C.NO_SIGNAL_NOTE in msg
    assert C.SUMMARY_TITLE not in msg  # 無訊號時不放摘要
    assert C.THRESHOLD_NOTE not in msg  # 門檻說明只在有訊號時附上


@pytest.mark.django_db
def test_signal_message_has_summary_plain_and_threshold_note(monkeypatch, settings):
    """有訊號：訊息含訊號摘要（含方向）、白話總結、指標附註、底部門檻說明。"""
    settings.DRY_RUN = True
    monkeypatch.setattr(runner.data, "fetch_daily", lambda symbol, days: _decreasing_df())
    monkeypatch.setattr(runner.data, "is_fresh_today", lambda df, market: True)

    call_command("run_notify", "--market", "tw")

    msg = PushLog.objects.first().message
    # 訊號摘要：4 檔 seed 標的皆觸發 rsi 多方，全部有訊號、方向偏多
    assert C.SUMMARY_TITLE in msg
    assert "4 檔有、0 檔無" in msg
    assert C.SUMMARY_DIR["bull"] in msg  # 方向標註（偏多）
    # 白話當主標、專業名詞退為「指標：」附註
    assert C.SIGNAL_PLAIN[("rsi", "bullish")] in msg
    assert "指標：" in msg
    # 底部門檻總說明
    assert C.THRESHOLD_NOTE in msg


@pytest.mark.django_db
def test_tw_message_contains_disclaimer(monkeypatch, settings):
    settings.DRY_RUN = True
    monkeypatch.setattr(runner.data, "fetch_daily", lambda symbol, days: _decreasing_df())
    monkeypatch.setattr(runner.data, "is_fresh_today", lambda df, market: True)

    call_command("run_notify", "--market", "tw")

    assert C.DISCLAIMER in PushLog.objects.first().message
