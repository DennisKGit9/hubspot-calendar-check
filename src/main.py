"""CLI entrypoint: fetch HubSpot busy times, clip to working hours, write busy.ics.

Usage:
  python -m src.main                # honor the 19:00 Berlin time guard
  python -m src.main --once         # build regardless of the current time
  python -m src.main --once --dry-run   # compute + print, write nothing
"""
from __future__ import annotations

import argparse
import sys

from .busy import compute_busy
from .config import Config
from .hubspot_client import fetch_busy_periods
from .ics_writer import write_ics
from .timeguard import should_run


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build a busy-slot iCalendar feed from a HubSpot meetings link.")
    p.add_argument("--once", action="store_true", help="Bypass the 19:00 Berlin time guard.")
    p.add_argument("--dry-run", action="store_true", help="Compute and print only; do not write the .ics file.")
    p.add_argument("--verbose", action="store_true", help="Print each busy block.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    config = Config()
    config.validate()

    if not args.once and not should_run(config):
        print(f"skipped: not the {config.target_hour}:00 {config.timezone} hour")
        return 0

    print(f"Fetching {config.months_ahead} month(s) of busy times for slug "
          f"{config.hubspot_slug!r} from {config.hubspot_api_base}")
    periods = fetch_busy_periods(config)
    print(f"Fetched {len(periods)} raw busy period(s)")

    busy = compute_busy(periods, config)
    print(f"Computed {len(busy)} busy block(s) within {config.work_start_hour:02d}:00-"
          f"{config.work_end_hour:02d}:00 {config.timezone}, days {sorted(config.work_days)}")

    if args.verbose or args.dry_run:
        for b in busy:
            print(f"  BUSY {b.start:%a %Y-%m-%d %H:%M} - {b.end:%H:%M}")

    if args.dry_run:
        print("dry-run: not writing the .ics file")
        return 0

    path = write_ics(busy, config)
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
