"""通報核心流程 — 由 run_notify 指令與 run_scheduler 排程器共用。

流程（api-design §1）：抓取 → 指標 → 防抖動 → 訊息 → 推播，全程記錄。
"""
import datetime as dt
import logging

from django.conf import settings
from django.utils import timezone

from notify import constants as C
from notify import data, discord_client, indicators, messaging
from notify.models import PushLog, SignalLog, WatchTarget

logger = logging.getLogger("notify")

US_NOTE = "（註：美股 21:00 尚未收盤，本資料為前一交易日收盤，非即時）"


def _recently_pushed(target: WatchTarget, sig: indicators.Signal) -> bool:
    """防抖動：同組合 24h 內已推過則跳過（feature-spec §3）。"""
    cutoff = timezone.now() - dt.timedelta(hours=24)
    return SignalLog.objects.filter(
        target=target,
        indicator=sig.indicator,
        direction=sig.direction,
        triggered_at__gte=cutoff,
    ).exists()


def _build_title() -> str:
    """訊息標題列（中性標籤 + 非投資建議標示）。

    每個時點都推全部標的，故標題不綁單一市場，統一用中性名稱。
    """
    return f"📈 {C.DAILY_TITLE} {timezone.localdate():%Y/%m/%d}　{C.NON_ADVICE_TAG}"


def run_market(market: str) -> str:
    """執行一個時點的通報，回傳可讀摘要字串。

    **到點必推**（feature-spec §6）：每個時點掃描全部啟用標的，價格區塊一定送出，
    有觸發的訊號才另外附上。`market` 只作為時段標籤與美股非即時註記的依據。
    """
    targets = WatchTarget.objects.filter(enabled=True)

    price_rows: list[messaging.PriceRow] = []
    signal_blocks: list[str] = []
    signaled: list[tuple[str, str]] = []  # (顯示名, 方向標註)，供訊號摘要用
    total_signals = 0

    for t in targets:
        try:
            df = data.fetch_daily(t.symbol, settings.DATA_LOOKBACK_DAYS)
        except data.DataError as e:
            # 抓取失敗仍列出該檔，不中斷其他標的
            logger.error("抓取失敗 %s: %s", t.symbol, e)
            price_rows.append(
                messaging.PriceRow(display_name=t.display_name, note=C.NOTE_NO_DATA)
            )
            continue

        last = df.index[-1]
        trigger_date = last.date() if hasattr(last, "date") else last
        close = float(df["close"].iloc[-1])
        prev_close = float(df["close"].iloc[-2])
        change_pct = (close - prev_close) / prev_close * 100 if prev_close else 0.0

        is_fresh = data.is_fresh_today(df, market)
        price_rows.append(
            messaging.PriceRow(
                display_name=t.display_name,
                date=trigger_date,
                close=close,
                change_pct=change_pct,
                note="" if is_fresh else C.NOTE_STALE,
            )
        )

        # 資料過舊：價格照列，但不得用舊資料產生新訊號（feature-spec §5）
        if not is_fresh:
            logger.warning("%s 今日未開盤/資料過舊，僅列價格不判定訊號", t.symbol)
            continue

        # 盤整過濾（A）：開關與閾值自 settings 讀取後傳入，indicators.py 保持無 Django 相依。
        sigs = indicators.evaluate(
            df,
            ranging_filter=settings.RANGING_FILTER_ENABLED,
            adx_threshold=settings.ADX_RANGING_THRESHOLD,
        )
        # L0 全域指標開關：只保留啟用清單內的指標
        sigs = [s for s in sigs if s.indicator in settings.ENABLED_INDICATORS]
        new_sigs = [s for s in sigs if not _recently_pushed(t, s)]
        if not new_sigs:
            continue

        now = timezone.now()
        for s in new_sigs:
            SignalLog.objects.create(
                target=t,
                indicator=s.indicator,
                direction=s.direction,
                trigger_date=trigger_date,
                triggered_at=now,
                detail=s.detail,
            )
        total_signals += len(new_sigs)
        msg = messaging.build_message(t.display_name, trigger_date, new_sigs)
        if msg:
            signal_blocks.append(msg)
            has_bull = any(s.direction == C.BULLISH for s in new_sigs)
            has_bear = any(s.direction == C.BEARISH for s in new_sigs)
            dir_key = "mixed" if has_bull and has_bear else ("bull" if has_bull else "bear")
            signaled.append((t.display_name, C.SUMMARY_DIR[dir_key]))

    parts = [_build_title()]
    price_block = messaging.build_price_block(price_rows)
    if price_block:
        parts.append(price_block)
    if total_signals == 0:
        parts.append(C.NO_SIGNAL_NOTE)
    else:
        signaled_set = {name for name, _ in signaled}
        no_signal_names = [
            r.display_name for r in price_rows if r.display_name not in signaled_set
        ]
        parts.append(messaging.build_signal_summary(signaled, no_signal_names))
    parts.extend(signal_blocks)
    if total_signals > 0:
        parts.append(C.THRESHOLD_NOTE)
    if market == "us":
        parts.append(US_NOTE)
    full = "\n\n".join(parts) + "\n\n" + "─" * 12 + "\n" + C.DISCLAIMER

    # 多頻道派送：每個啟用的通報線各推一次、各記一筆 PushLog（互不影響）
    channels: list[tuple[str, object]] = []
    if settings.DISCORD_ENABLED:
        channels.append(("discord", discord_client.push))

    push_summaries: list[str] = []
    for name, pusher in channels:
        result = pusher(full)
        PushLog.objects.create(
            channel=name,
            market=market,
            push_mode=result.mode,
            message=full,
            signal_count=total_signals,
            status=result.status,
            error=result.error,
        )
        push_summaries.append(f"{name}={result.status}/{result.mode}")

    if not channels:
        logger.warning("無啟用的推播頻道（DISCORD_ENABLED 關閉）")
        push_summaries.append("none")

    logger.info(
        "market=%s 價格 %d 檔、訊號 %d 筆，推播 %s",
        market,
        len(price_rows),
        total_signals,
        " ".join(push_summaries),
    )
    return (
        f"[{market}] 價格 {len(price_rows)} 檔、訊號 {total_signals} 筆，"
        f"推播 {' '.join(push_summaries)}"
    )
