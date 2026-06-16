"""Turn raw busy periods into working-hours busy blocks for the calendar feed.

Each booked period from HubSpot is clipped to the configured working window
(09:00-18:00 Berlin) on weekdays, split per day, trimmed to drop the past, and
overlapping/adjacent results are merged into clean blocks.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .config import Config
from .hubspot_client import BusyPeriod


@dataclass(frozen=True)
class BusySlot:
    start: datetime  # timezone-aware, Berlin local
    end: datetime  # timezone-aware, Berlin local


def compute_busy(
    periods: list[BusyPeriod],
    config: Config,
    now: datetime | None = None,
) -> list[BusySlot]:
    tz = ZoneInfo(config.timezone)
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)

    slots: list[BusySlot] = []
    for period in periods:
        start = period.start.astimezone(tz)
        end = period.end.astimezone(tz)

        day = start.date()
        last_day = end.date()
        while day <= last_day:
            if day.weekday() in config.work_days:
                win_start = datetime(day.year, day.month, day.day, config.work_start_hour, 0, tzinfo=tz)
                win_end = datetime(day.year, day.month, day.day, config.work_end_hour, 0, tzinfo=tz)
                seg_start = max(start, win_start)
                seg_end = min(end, win_end)
                # Drop fully-past segments; trim a segment that is partly past.
                if seg_end.astimezone(timezone.utc) > now:
                    if seg_start.astimezone(timezone.utc) < now:
                        seg_start = now.astimezone(tz)
                    if seg_start < seg_end:
                        slots.append(BusySlot(start=seg_start, end=seg_end))
            day += timedelta(days=1)

    return _merge(slots)


def _merge(slots: list[BusySlot]) -> list[BusySlot]:
    if not slots:
        return []
    slots = sorted(slots, key=lambda s: s.start)
    merged = [slots[0]]
    for s in slots[1:]:
        last = merged[-1]
        if s.start <= last.end:  # overlapping or adjacent
            if s.end > last.end:
                merged[-1] = BusySlot(start=last.start, end=s.end)
        else:
            merged.append(s)
    return merged
