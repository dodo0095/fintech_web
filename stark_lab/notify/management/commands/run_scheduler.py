"""常駐排程器 — 依 .env 設定的時間自動執行 tw/us 通報。

用法（前景常駐，Ctrl+C 停止）：
    python manage.py run_scheduler

開關：.env 的 SCHEDULER_ENABLED=false 時不啟動。
時間：SCHEDULE_TW / SCHEDULE_US（HH:MM，台灣時間）。星期遮罩見 _day_of_week：
台股與美股盤前（21:00）為週一至五；美股盤後清晨槽（如 04:00）為週二至六
（對應美股週一至週五收盤，含台灣週六）。
"""
import logging

import pytz
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from django.conf import settings
from django.core.management.base import BaseCommand

from notify import runner

logger = logging.getLogger("notify")


def _parse_hhmm(value: str) -> tuple[int, int]:
    """'09:00' -> (9, 0)；格式錯誤時 raise ValueError。"""
    hh, mm = value.strip().split(":")
    h, m = int(hh), int(mm)
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError(f"時間超出範圍: {value}")
    return h, m


def _parse_times(value: str) -> list[tuple[int, int]]:
    """'09:00,14:00' -> [(9, 0), (14, 0)]；每市場可設多個時段（逗號分隔）。"""
    return [_parse_hhmm(v) for v in value.split(",") if v.strip()]


def _day_of_week(market: str, hour: int) -> str:
    """回傳該市場／時段對應的 cron 星期遮罩。

    美股盤後的清晨時段（如 04:00，台灣時間）拿的是「前一交易日」的收盤，
    因此星期比美股交易日晚一天：美股週一~週五收盤 → 台灣週二~週六才拿得到。
    這一槽必須用 tue-sat，否則美股週五整場的通報會在台灣週六被漏掉。
    其餘時段（台股、美股盤前 21:00）維持 mon-fri。
    """
    if market == "us" and hour < 12:
        return "tue-sat"
    return "mon-fri"


def _safe_run(market: str) -> None:
    """單一市場執行；例外只記錄、不讓排程器整個掛掉。"""
    try:
        summary = runner.run_market(market)
        logger.info("排程執行完成 %s", summary)
    except Exception:  # noqa: BLE001
        logger.exception("排程執行失敗 market=%s", market)


def build_scheduler() -> BlockingScheduler:
    """依設定建立排程器並為每市場的每個時段各掛一個工作（不啟動）。"""
    tz = pytz.timezone(settings.TIME_ZONE)
    scheduler = BlockingScheduler(timezone=tz)

    for market, spec in (("tw", settings.SCHEDULE_TW), ("us", settings.SCHEDULE_US)):
        for h, m in _parse_times(spec):
            scheduler.add_job(
                _safe_run,
                CronTrigger(
                    day_of_week=_day_of_week(market, h),
                    hour=h,
                    minute=m,
                    timezone=tz,
                ),
                args=[market],
                id=f"{market}-{h:02d}{m:02d}",
                replace_existing=True,
            )
    return scheduler


class Command(BaseCommand):
    help = "常駐排程器：依 .env 設定時間自動執行 tw/us 通報"

    def handle(self, *args, **options):
        if not settings.SCHEDULER_ENABLED:
            self.stdout.write("SCHEDULER_ENABLED=false，排程器未啟動。")
            return

        scheduler = build_scheduler()
        self.stdout.write(
            f"排程器啟動：tw={settings.SCHEDULE_TW}、us={settings.SCHEDULE_US} "
            f"（{settings.TIME_ZONE}；美股盤後清晨槽含週六）。按 Ctrl+C 停止。"
        )
        logger.info("排程器啟動 tw=%s us=%s", settings.SCHEDULE_TW, settings.SCHEDULE_US)
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            self.stdout.write("排程器已停止。")
