"""Configuration loaded from environment variables.

Every value has a sensible default so the tool runs out of the box for the
`dennis-kwiatkowski` link. Override any value via environment variables (or a
local `.env` file, which is loaded automatically when python-dotenv is present).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

try:  # local convenience only; absent/no-op in CI
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is optional
    pass


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    return default if raw is None or raw.strip() == "" else int(raw)


def _str(name: str, default: str) -> str:
    raw = os.environ.get(name)
    return default if raw is None or raw.strip() == "" else raw.strip()


def _work_days(default: tuple[int, ...]) -> tuple[int, ...]:
    raw = os.environ.get("WORK_DAYS")
    if not raw or not raw.strip():
        return default
    return tuple(int(p) for p in raw.split(",") if p.strip() != "")


@dataclass(frozen=True)
class Config:
    hubspot_slug: str = field(default_factory=lambda: _str("HUBSPOT_SLUG", "dennis-kwiatkowski"))
    # Regional HubSpot API gateway that serves the public meetings endpoints.
    # EU portals use api-eu1.hubapi.com; US portals use api.hubapi.com.
    hubspot_api_base: str = field(default_factory=lambda: _str("HUBSPOT_API_BASE", "https://api-eu1.hubapi.com"))
    availability_path: str = field(
        default_factory=lambda: _str("HUBSPOT_AVAILABILITY_PATH", "/meetings-public/v3/book/availability-page")
    )
    # Public meetings page host, used for Referer/Origin headers.
    referer_base: str = field(default_factory=lambda: _str("HUBSPOT_REFERER_BASE", "https://meetings-eu1.hubspot.com"))
    # How many monthly availability pages to fetch (monthOffset 0..N-1).
    months_ahead: int = field(default_factory=lambda: _int("MONTHS_AHEAD", 3))

    work_start_hour: int = field(default_factory=lambda: _int("WORK_START_HOUR", 9))
    work_end_hour: int = field(default_factory=lambda: _int("WORK_END_HOUR", 18))
    work_days: tuple[int, ...] = field(default_factory=lambda: _work_days((0, 1, 2, 3, 4)))
    timezone: str = field(default_factory=lambda: _str("TIMEZONE", "Europe/Berlin"))
    target_hour: int = field(default_factory=lambda: _int("TARGET_HOUR", 19))
    output_path: str = field(default_factory=lambda: _str("OUTPUT_PATH", "output/busy.ics"))
    calendar_name: str = field(default_factory=lambda: _str("CALENDAR_NAME", "HubSpot Busy"))

    def availability_url(self, month_offset: int) -> str:
        base = self.hubspot_api_base.rstrip("/")
        path = self.availability_path
        return (
            f"{base}{path}?slug={self.hubspot_slug}"
            f"&monthOffset={month_offset}&timezone={self.timezone}"
        )

    def validate(self) -> None:
        if not self.hubspot_slug:
            raise ValueError("HUBSPOT_SLUG must not be empty")
        if not (0 <= self.work_start_hour < self.work_end_hour <= 24):
            raise ValueError("WORK_START_HOUR/WORK_END_HOUR are out of range")
        if not self.work_days:
            raise ValueError("WORK_DAYS resolved to an empty set")
        if self.months_ahead < 1:
            raise ValueError("MONTHS_AHEAD must be >= 1")
