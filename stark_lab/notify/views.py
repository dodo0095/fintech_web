"""唯讀維運 Dashboard（api-design §5）。

⚠️ 隱藏而非上鎖：`localhost_only` 檢查 REMOTE_ADDR，但正式部署走
Caddy→waitress 時 REMOTE_ADDR 恆為 127.0.0.1，等同放行所有人。本版僅以
「非顯眼路徑 + noindex + robots Disallow」做隱藏，尚未加登入鎖，勿視為存取控制。
"""
import functools

import pytz
from django.conf import settings
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.utils import timezone

from notify import constants as C
from notify.management.commands.run_scheduler import build_scheduler
from notify.models import PushLog, SignalLog, WatchTarget

LOCAL_ADDRS = {"127.0.0.1", "::1"}


def localhost_only(view):
    """僅允許本機連線；其他來源一律 403。"""

    @functools.wraps(view)
    def _wrapped(request, *args, **kwargs):
        if request.META.get("REMOTE_ADDR") not in LOCAL_ADDRS:
            return HttpResponseForbidden("僅限本機存取")
        return view(request, *args, **kwargs)

    return _wrapped


def _next_runs():
    """下次排程觸發時間（不啟動排程器，只讀 trigger）。"""
    tz = pytz.timezone(settings.TIME_ZONE)
    now = timezone.localtime()
    runs = []
    try:
        for job in build_scheduler().get_jobs():
            nxt = job.trigger.get_next_fire_time(None, now)
            if nxt:
                market = job.id.split("-")[0]
                runs.append(
                    {
                        "label": C.MARKET_LABEL.get(market, market),
                        "at": nxt.astimezone(tz),
                    }
                )
    except ValueError:
        return []  # SCHEDULE_* 設定格式錯誤
    return sorted(runs, key=lambda r: r["at"])


def _push_rows():
    return [
        {
            "at": p.created_at,
            "market": C.MARKET_LABEL.get(p.market, p.market),
            "status": p.status,
            "ok": p.status == "success",
            "failed": p.status == "failed",
            "signal_count": p.signal_count,
        }
        for p in PushLog.objects.order_by("-id")[:10]
    ]


def _signal_rows():
    return [
        {
            "at": s.triggered_at,
            "name": s.target.display_name,
            "indicator": s.indicator.upper(),
            "bullish": s.direction == C.BULLISH,
        }
        for s in SignalLog.objects.select_related("target").order_by("-id")[:8]
    ]


@localhost_only
def dashboard(request):
    response = render(
        request,
        "notify/dashboard.html",
        {
            "dry_run": settings.DRY_RUN,
            "scheduler_enabled": settings.SCHEDULER_ENABLED,
            "next_runs": _next_runs()[:4],
            "pushes": _push_rows(),
            "signals": _signal_rows(),
            "targets": WatchTarget.objects.all(),
            "now": timezone.localtime(),
        },
    )
    # 隱藏：明確標示不予索引（搭配 robots.txt Disallow /_ops/）
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response
