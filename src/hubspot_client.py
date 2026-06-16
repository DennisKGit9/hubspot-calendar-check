"""Fetch the host's booked/busy time blocks from the public HubSpot meetings API.

Confirmed endpoint (no auth required), EU portal:

    GET https://api-eu1.hubapi.com/meetings-public/v3/book/availability-page
        ?slug=<slug>&monthOffset=<n>&timezone=<tz>

The JSON response includes `allUsersBusyTimes[].busyTimes`, the host's actual
busy periods (merged) as `{start, end}` epoch-millis UTC — i.e. exactly the slots
that are already booked. We fetch one page per month (monthOffset 0..N-1) and
union the busy periods. A browser-like User-Agent is sent for good measure.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import requests

from .config import Config

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


@dataclass(frozen=True)
class BusyPeriod:
    start: datetime  # timezone-aware, UTC
    end: datetime  # timezone-aware, UTC


def fetch_busy_periods(config: Config, session: requests.Session | None = None) -> list[BusyPeriod]:
    sess = session or requests.Session()
    headers = dict(_HEADERS)
    headers["Referer"] = f"{config.referer_base.rstrip('/')}/{config.hubspot_slug}"
    headers["Origin"] = config.referer_base.rstrip("/")

    periods: list[BusyPeriod] = []
    seen: set[tuple[int, int]] = set()
    for month in range(config.months_ahead):
        url = config.availability_url(month)
        resp = sess.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(
                f"HubSpot returned HTTP {resp.status_code} for {url}\n"
                f"First 300 chars: {resp.text[:300]!r}"
            )
        try:
            data = resp.json()
        except ValueError as exc:
            raise RuntimeError(
                f"HubSpot response was not JSON ({url}); first 300 chars: {resp.text[:300]!r}"
            ) from exc
        for raw in _extract_busy(data):
            key = (raw[0], raw[1])
            if key in seen:
                continue
            seen.add(key)
            periods.append(
                BusyPeriod(
                    start=datetime.fromtimestamp(raw[0] / 1000, tz=timezone.utc),
                    end=datetime.fromtimestamp(raw[1] / 1000, tz=timezone.utc),
                )
            )

    periods.sort(key=lambda p: p.start)
    return periods


def _extract_busy(data: dict) -> list[tuple[int, int]]:
    """Pull every {start,end} pair from allUsersBusyTimes[*].busyTimes."""
    out: list[tuple[int, int]] = []
    users = data.get("allUsersBusyTimes") if isinstance(data, dict) else None
    if not isinstance(users, list):
        raise RuntimeError(
            "Could not locate 'allUsersBusyTimes' in HubSpot response. "
            f"Top-level keys: {sorted(data.keys()) if isinstance(data, dict) else type(data)}"
        )
    for user in users:
        if not isinstance(user, dict):
            continue
        busy = user.get("busyTimes") or user.get("busyTimesUnmerged") or []
        for entry in busy:
            if not isinstance(entry, dict):
                continue
            start = entry.get("start")
            end = entry.get("end")
            if start is None or end is None or end <= start:
                continue
            out.append((int(start), int(end)))
    return out
