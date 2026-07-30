"""關注事件（非農等）→ events payload（自 fetch_events.py 移植）。"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from .common import now_iso

# 已知高影響事件靜態行事曆（依官方更新）
CALENDAR = [
    {
        "name": "非農就業",
        "date": "2026-08-07",
        "actual": None,
        "forecast": 175000,
        "previous": 206000,
        "unit": "人",
        "note": "美國非農就業報告（預估日程，請依官方確認）",
    },
    {
        "name": "非農就業",
        "date": "2026-09-04",
        "actual": None,
        "forecast": None,
        "previous": None,
        "unit": "人",
        "note": "預估日程",
    },
]


def should_show(event_date: date, today: date) -> bool:
    return (today - timedelta(days=3)) <= event_date <= (today + timedelta(days=14))


def build() -> dict:
    today = datetime.now().date()
    events = []
    for raw in CALENDAR:
        try:
            d = date.fromisoformat(raw["date"])
        except ValueError:
            continue
        events.append(
            {
                "name": raw["name"],
                "date": raw["date"],
                "actual": raw.get("actual"),
                "forecast": raw.get("forecast"),
                "previous": raw.get("previous"),
                "unit": raw.get("unit", "人"),
                "note": raw.get("note", ""),
                "visible": should_show(d, today),
            }
        )
    return {"updated_at": now_iso(), "events": events}
