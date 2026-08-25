"""In-process news refresh so the live site does not depend on someone running update_news by hand.

Slots: 04:00 / 08:00 / 14:00 / 20:00 Taipei. If a slot was missed and data is
stale (>10h), catch up once.
"""
from __future__ import annotations

import logging
import os
import sys
import threading
import time
from datetime import datetime, timedelta

log = logging.getLogger("news.scheduler")

SLOTS = (4, 8, 14, 20)
STALE_HOURS = 10
_started = False
_lock = threading.Lock()
_running = False


def _taipei_now():
    from news.fetchers.common import TW
    return datetime.now(TW)


def _parse_ran_at(raw):
    from news.fetchers.common import TW
    if not raw:
        return None
    text = str(raw).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TW)
    return dt


def _is_stale():
    from news import store
    status = store.read_status() or {}
    ran = _parse_ran_at(status.get("ran_at"))
    if ran is None:
        return True
    return _taipei_now() - ran.astimezone(ran.tzinfo) > timedelta(hours=STALE_HOURS)


def _run_update(reason):
    global _running
    with _lock:
        if _running:
            return
        _running = True
    try:
        log.info("auto update_news start (%s)", reason)
        from django.core.management import call_command
        call_command("update_news")
        log.info("auto update_news done (%s)", reason)
    except Exception:
        log.exception("auto update_news failed (%s)", reason)
    finally:
        with _lock:
            _running = False


def _loop():
    last_slot = ""
    time.sleep(8)
    if _is_stale():
        _run_update("startup-stale")
        last_slot = _taipei_now().strftime("%Y-%m-%d-%H")
    while True:
        try:
            now = _taipei_now()
            slot = now.strftime("%Y-%m-%d-%H")
            due = now.hour in SLOTS and now.minute < 12
            if due and slot != last_slot:
                _run_update("slot-%02d" % now.hour)
                last_slot = slot
            elif _is_stale() and now.minute in (0, 1, 2):
                _run_update("stale")
                last_slot = slot
        except Exception:
            log.exception("scheduler tick failed")
        time.sleep(30)


def _should_start():
    if any(x in sys.argv for x in ("test", "migrate", "makemigrations", "shell", "collectstatic")):
        return False
    if "runserver" in sys.argv:
        return os.environ.get("RUN_MAIN") == "true"
    return True


def start():
    global _started
    if not _should_start():
        return
    if _started:
        return
    _started = True
    t = threading.Thread(target=_loop, name="news-updater", daemon=True)
    t.start()
    log.info("news auto-updater thread started")
