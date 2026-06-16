"""Render busy slots into a subscribable iCalendar (.ics) feed.

Each run writes a full snapshot of the current busy state. Event UIDs are
deterministic (derived from the slot's UTC start/end) so re-publishing updates
the same events rather than duplicating them, and slots that free up simply
vanish from the next snapshot.
"""
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone

from icalendar import Calendar, Event

from .busy import BusySlot
from .config import Config

_SUMMARY = "Booked (HubSpot)"
_DESCRIPTION = (
    "Auto-generated busy block inferred from a public HubSpot meetings link. "
    "Managed by hubspot-calendar-check."
)


def _uid(slug: str, slot: BusySlot) -> str:
    start = slot.start.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    end = slot.end.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    digest = hashlib.sha1(f"{slug}|{start}|{end}".encode()).hexdigest()
    return f"{digest}@hubspot-calendar-check"


def build_calendar(busy_slots: list[BusySlot], config: Config, now: datetime | None = None) -> Calendar:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)

    cal = Calendar()
    cal.add("prodid", "-//hubspot-calendar-check//busy feed//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", config.calendar_name)
    cal.add("x-wr-timezone", config.timezone)

    for slot in busy_slots:
        event = Event()
        event.add("uid", _uid(config.hubspot_slug, slot))
        event.add("summary", _SUMMARY)
        event.add("description", _DESCRIPTION)
        # Emit absolute UTC instants (…Z). Each is DST-correct (computed via
        # zoneinfo) and needs no VTIMEZONE, maximizing client compatibility.
        event.add("dtstart", slot.start.astimezone(timezone.utc))
        event.add("dtend", slot.end.astimezone(timezone.utc))
        event.add("dtstamp", now)
        event.add("last-modified", now)
        event.add("transp", "OPAQUE")  # show as Busy
        cal.add_component(event)

    return cal


def write_ics(busy_slots: list[BusySlot], config: Config, now: datetime | None = None) -> str:
    cal = build_calendar(busy_slots, config, now=now)
    path = config.output_path
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(cal.to_ical())
    return path
