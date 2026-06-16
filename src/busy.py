"""Compute booked/busy slots as the complement of the open availability.

The public page only lists OPEN slots. Within the working-hours grid
(09:00-18:00 Berlin, Mon-Fri at the link's slot length), any cell that is NOT
open is treated as booked. Past cells are skipped so the feed never carries
busy events for time that has already elapsed.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .config import Config
from .hubspot_client import Availability


@dataclass(frozen=True)
class BusySlot:
    start: datetime  # timezone-aware, Berlin local
    end: datetime  # timezone-aware, Berlin local


def _minute_key(dt: datetime) -> datetime:
    return dt.replace(second=0, microsecond=0)


def compute_busy(
    availability: Availability,
    config: Config,
    now: datetime | None = None,
) -> list[BusySlot]:
    tz = ZoneInfo(config.timezone)
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)

    step = timedelta(minutes=availability.duration_minutes or 30)
    step_min = int(step.total_seconds() // 60)

    # Set of OPEN slot starts, keyed by Berlin-local minute.
    available_keys = {
        _minute_key(s.start.astimezone(tz)) for s in availability.slots
    }

    if not availability.slots:
        return []

    starts = [s.start.astimezone(tz) for s in availability.slots]
    ends = [s.end.astimezone(tz) for s in availability.slots]
    first_date = min(starts).date()
    last_date = max(ends).date()

    # Phase-align the grid to the observed availability cadence, in case slots do
    # not start exactly on `work_start_hour` (buffers/custom start times).
    sample = min(starts)
    minutes_from_workstart = (sample.hour * 60 + sample.minute) - config.work_start_hour * 60
    phase = minutes_from_workstart % step_min if step_min else 0

    busy: list[BusySlot] = []
    day = first_date
    while day <= last_date:
        if day.weekday() in config.work_days:
            cursor = datetime(
                day.year, day.month, day.day, config.work_start_hour, 0, tzinfo=tz
            ) + timedelta(minutes=phase)
            day_end = datetime(
                day.year, day.month, day.day, config.work_end_hour, 0, tzinfo=tz
            )
            while cursor + step <= day_end:
                if cursor.astimezone(timezone.utc) >= now:  # skip past cells
                    if _minute_key(cursor) not in available_keys:
                        busy.append(BusySlot(start=cursor, end=cursor + step))
                cursor += step
        day += timedelta(days=1)

    return _merge_adjacent(busy)


def _merge_adjacent(slots: list[BusySlot]) -> list[BusySlot]:
    """Collapse consecutive busy cells into single contiguous blocks."""
    if not slots:
        return []
    slots = sorted(slots, key=lambda s: s.start)
    merged = [slots[0]]
    for s in slots[1:]:
        last = merged[-1]
        if s.start <= last.end:  # contiguous (or overlapping)
            if s.end > last.end:
                merged[-1] = BusySlot(start=last.start, end=s.end)
        else:
            merged.append(s)
    return merged
