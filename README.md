# hubspot-calendar-check

Publishes a **subscribable calendar feed** (`.ics`) of the time slots that are
already **booked** on a public HubSpot meetings link, so you can see your booked
availability in any calendar app.

The tool reads the host's actual booked/busy blocks from the meetings link's
public availability API, clips them to working hours (**09:00–18:00 Berlin,
Mon–Fri**), and emits each as a busy block titled **"Booked (HubSpot)"**.

A GitHub Action rebuilds the feed **once a day at 19:00 CET/CEST** and publishes
it to GitHub Pages. You subscribe to the URL once; your calendar re-polls it
automatically.

> **Feed URL:** `https://denniskgit9.github.io/hubspot-calendar-check/busy.ics`

## How it works

1. `src/hubspot_client.py` fetches the public availability API
   (`api-eu1.hubapi.com/meetings-public/v3/book/availability-page`, no auth) for
   the next few months and reads `allUsersBusyTimes[].busyTimes` — the host's
   real booked periods.
2. `src/busy.py` clips each booked period to 09:00–18:00 on weekdays, drops past
   time, and merges overlapping/adjacent blocks.
3. `src/ics_writer.py` writes a full-snapshot `output/busy.ics` with deterministic
   event UIDs (re-publishing updates events in place; freed slots disappear).
4. `.github/workflows/sync.yml` runs daily and force-pushes the feed to the
   `gh-pages` branch (served by Pages "Deploy from a branch" — no Actions
   artifact storage involved). Two UTC crons (17:00 + 18:00) cover DST;
   `src/timeguard.py` lets only the run that is 19:00 in Berlin proceed.

## One-time setup

1. **Run the workflow once:** **Actions → hubspot-busy-ics → Run workflow**
   (leave "Bypass the time guard" checked). This builds the feed and force-pushes
   it to the `gh-pages` branch.
2. **Enable GitHub Pages:** repo **Settings → Pages → Source = "Deploy from a
   branch"**, branch **`gh-pages`**, folder **`/ (root)`**.
3. **Subscribe in Google Calendar:** *Other calendars → ＋ → Subscribe to
   calendar / From URL* → paste the feed URL above. (Apple/Outlook calendars work
   the same way via their "subscribe to calendar" option.)

Google refreshes subscribed URLs on its own cadence (often several hours up to a
day) — this is a Google behavior, not something the feed controls.

No secrets are required: the HubSpot endpoint is public and the push to
`gh-pages` uses the built-in `GITHUB_TOKEN`.

> **Note:** GitHub Pages on a **private** repo requires a paid plan (Pro/Team).
> If the repo is private and on the Free plan, either make it public or host the
> generated `busy.ics` somewhere with a public HTTPS URL.

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
| `HUBSPOT_API_BASE` | `https://api-eu1.hubapi.com` | Regional API gateway (EU; use `https://api.hubapi.com` for US) |
| `HUBSPOT_AVAILABILITY_PATH` | `/meetings-public/v3/book/availability-page` | Public availability endpoint path |
| `HUBSPOT_REFERER_BASE` | `https://meetings-eu1.hubspot.com` | Meetings page host (Referer/Origin headers) |
| `MONTHS_AHEAD` | `3` | Months of availability to fetch (monthOffset 0…N-1) |
| `WORK_START_HOUR` / `WORK_END_HOUR` | `9` / `18` | Working-hours window (Berlin) |
| `WORK_DAYS` | `0,1,2,3,4` | Weekdays to consider (Mon=0 … Sun=6) |
| `TIMEZONE` | `Europe/Berlin` | Link timezone |
| `TARGET_HOUR` | `19` | Local hour the daily run fires |
| `OUTPUT_PATH` | `output/busy.ics` | Generated feed path |
| `CALENDAR_NAME` | `HubSpot Busy` | Subscribed calendar display name |

## Caveats

- The API exposes only free/busy timing — no meeting titles or attendees, so
  events are generic busy blocks.
- Busy blocks come from the host's connected calendar, clipped to working hours;
  buffers/min-notice are not included (only actual booked/blocked time).
- If HubSpot changes the JSON shape, `fetch_busy_periods` raises with a
  diagnostic snippet — confirm the live request in your browser's network tab and
  adjust `HUBSPOT_API_BASE` / `HUBSPOT_AVAILABILITY_PATH` or the parser.
