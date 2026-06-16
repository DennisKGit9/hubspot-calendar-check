# hubspot-calendar-check

Publishes a **subscribable calendar feed** (`.ics`) of the time slots that are
already **booked** on a public HubSpot meetings link, so you can see your booked
availability in any calendar app.

The HubSpot page (`https://meetings-eu1.hubspot.com/dennis-kwiatkowski`) only
shows *open* slots. This tool inverts that: within working hours
(**09:00–18:00 Berlin, Mon–Fri**, at the link's slot length) any slot that is
**not** open is treated as booked and emitted as a busy block titled
**"Booked (HubSpot)"**.

A GitHub Action rebuilds the feed **once a day at 19:00 CET/CEST** and publishes
it to GitHub Pages. You subscribe to the URL once; your calendar re-polls it
automatically.

> **Feed URL:** `https://denniskgit9.github.io/hubspot-calendar-check/busy.ics`

## How it works

1. `src/hubspot_client.py` fetches the public availability JSON (browser-like
   headers — the endpoint 403s plain clients).
2. `src/busy.py` computes booked slots = working-hours grid **minus** open slots
   (past slots skipped; contiguous busy cells merged into one block).
3. `src/ics_writer.py` writes a full-snapshot `output/busy.ics` with deterministic
   event UIDs (re-publishing updates events in place; freed slots disappear).
4. `.github/workflows/sync.yml` runs daily and deploys the feed to Pages. Two UTC
   crons (17:00 + 18:00) cover DST; `src/timeguard.py` lets only the run that is
   19:00 in Berlin proceed.

## One-time setup

1. **Enable GitHub Pages:** repo **Settings → Pages → Source = "GitHub Actions"**.
2. **Run the workflow once:** **Actions → hubspot-busy-ics → Run workflow**
   (leave "Bypass the time guard" checked). This builds and deploys the feed.
3. **Subscribe in Google Calendar:** *Other calendars → ＋ → Subscribe to
   calendar / From URL* → paste the feed URL above. (Apple/Outlook calendars work
   the same way via their "subscribe to calendar" option.)

Google refreshes subscribed URLs on its own cadence (often several hours up to a
day) — this is a Google behavior, not something the feed controls.

No secrets are required: the HubSpot endpoint is public and the Pages deploy uses
the built-in `GITHUB_TOKEN`.

## Run / test locally

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Compute and print booked slots without writing anything:
python -m src.main --once --dry-run

# Actually write output/busy.ics:
python -m src.main --once
```

Copy `.env.example` → `.env` to override any defaults (slug, working hours,
timezone, output path). All values are optional.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `HUBSPOT_SLUG` | `dennis-kwiatkowski` | Meetings link slug |
| `HUBSPOT_BASE` | `https://meetings-eu1.hubspot.com` | Portal host |
| `HUBSPOT_ENDPOINT_TEMPLATE` | `{base}/api/booking/v1/meetings/book/{slug}` | Availability endpoint |
| `WORK_START_HOUR` / `WORK_END_HOUR` | `9` / `18` | Working-hours window (Berlin) |
| `WORK_DAYS` | `0,1,2,3,4` | Weekdays to consider (Mon=0 … Sun=6) |
| `TIMEZONE` | `Europe/Berlin` | Link timezone |
| `TARGET_HOUR` | `19` | Local hour the daily run fires |
| `OUTPUT_PATH` | `output/busy.ics` | Generated feed path |
| `CALENDAR_NAME` | `HubSpot Busy` | Subscribed calendar display name |

## Caveats

- The public page exposes only free/busy — no meeting titles or attendees, so
  events are generic busy blocks.
- "Booked" can't be distinguished from other blocked time (buffers, time-off);
  any unavailable working-hour slot is treated as busy.
- If HubSpot changes the availability JSON shape, `fetch_availability` raises with
  a diagnostic snippet — confirm the live request in your browser's network tab
  and adjust `HUBSPOT_ENDPOINT_TEMPLATE` or the parser.
