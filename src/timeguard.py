"""Decide whether *now* is the once-a-day slot the feed should rebuild on.

GitHub Actions cron is UTC and has no concept of DST, so the workflow fires at
both 17:00 and 18:00 UTC. This guard lets exactly one of those runs proceed: the
one where the local (Europe/Berlin) wall-clock hour equals `target_hour` (19).

  - Summer (CEST, UTC+2): 17:00 UTC == 19:00 Berlin -> run; 18:00 UTC == 20:00 -> skip
  - Winter (CET,  UTC+1): 18:00 UTC == 19:00 Berlin -> run; 17:00 UTC == 18:00 -> skip
"""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from .config import Config


def should_run(config: Config, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    local = now.astimezone(ZoneInfo(config.timezone))
    return local.hour == config.target_hour
