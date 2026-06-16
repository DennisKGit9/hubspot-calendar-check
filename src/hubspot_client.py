"""Fetch and parse the *public* availability JSON behind a HubSpot meetings link.

The embeddable meetings widget loads open time slots from a public (no-login)
JSON endpoint in the `/api/booking/v1/meetings/book/{slug}` family. The endpoint
rejects non-browser clients with HTTP 403, so we send browser-like headers.

The response is large and its exact shape can change. We therefore parse
defensively: we walk the JSON for `linkAvailabilityByDuration` (a map keyed by
meeting duration in milliseconds) and read the slot list under the finest
duration offered. If the shape ever changes, `fetch_availability` raises with a
diagnostic snippet — confirm the live shape by opening the link in a browser and
inspecting the XHR/fetch request in the network tab, then adjust the parser or
`HUBSPOT_ENDPOINT_TEMPLATE`.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import requests

from .config import Config

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


@dataclass(frozen=True)
class TimeSlot:
    start: datetime  # timezone-aware, UTC
    end: datetime  # timezone-aware, UTC


@dataclass(frozen=True)
class Availability:
    slots: list[TimeSlot]  # OPEN/bookable slots
    duration_minutes: int


def fetch_availability(config: Config, session: requests.Session | None = None) -> Availability:
    url = config.endpoint_url
    headers = dict(_BROWSER_HEADERS)
    headers["Referer"] = f"{config.hubspot_base.rstrip('/')}/{config.hubspot_slug}"
    headers["Origin"] = config.hubspot_base.rstrip("/")

    sess = session or requests.Session()
    resp = sess.get(url, headers=headers, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(
            f"HubSpot returned HTTP {resp.status_code} for {url}\n"
            f"First 300 chars of body: {resp.text[:300]!r}"
        )
    try:
        data = resp.json()
    except ValueError as exc:
        raise RuntimeError(
            f"HubSpot response was not JSON ({url}); first 300 chars: {resp.text[:300]!r}"
        ) from exc

    return parse_availability(data)


def parse_availability(data: dict) -> Availability:
    by_duration = _find_key(data, "linkAvailabilityByDuration")
    if not isinstance(by_duration, dict) or not by_duration:
        raise RuntimeError(
            "Could not locate 'linkAvailabilityByDuration' in HubSpot response. "
            f"Top-level keys seen: {sorted(data.keys()) if isinstance(data, dict) else type(data)}"
        )

    # Pick the finest duration offered -> most precise busy grid.
    duration_ms = min(int(k) for k in by_duration.keys())
    entries = by_duration[str(duration_ms)] if str(duration_ms) in by_duration else by_duration[duration_ms]

    # `entries` is usually a list of {startMillisUtc, endMillisUtc}; tolerate an
    # object wrapping that list under common keys.
    if isinstance(entries, dict):
        entries = (
            entries.get("availabilities")
            or entries.get("slots")
            or entries.get("times")
            or []
        )
    if not isinstance(entries, list):
        raise RuntimeError(f"Unexpected availability entries type: {type(entries)}")

    slots: list[TimeSlot] = []
    for e in entries:
        start_ms = e.get("startMillisUtc") if isinstance(e, dict) else None
        end_ms = e.get("endMillisUtc") if isinstance(e, dict) else None
        if start_ms is None:
            start_ms = e.get("start") if isinstance(e, dict) else None
        if start_ms is None:
            continue
        start = datetime.fromtimestamp(int(start_ms) / 1000, tz=timezone.utc)
        if end_ms is not None:
            end = datetime.fromtimestamp(int(end_ms) / 1000, tz=timezone.utc)
        else:
            end = datetime.fromtimestamp((int(start_ms) + duration_ms) / 1000, tz=timezone.utc)
        slots.append(TimeSlot(start=start, end=end))

    slots.sort(key=lambda s: s.start)
    return Availability(slots=slots, duration_minutes=duration_ms // 60000)


def _find_key(obj, target: str):
    """Depth-first search for the first value under `target` anywhere in the JSON."""
    if isinstance(obj, dict):
        if target in obj:
            return obj[target]
        for v in obj.values():
            found = _find_key(v, target)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _find_key(v, target)
            if found is not None:
                return found
    return None
