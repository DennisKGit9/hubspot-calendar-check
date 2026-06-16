"""One-shot endpoint discovery (run in CI, where HubSpot is reachable).

Fetches the public meetings page, surfaces any embedded JSON / API references,
and probes candidate availability endpoints. Read the job log to identify the
real availability endpoint, then delete this file + workflow.
"""
from __future__ import annotations

import json
import re

import requests

BASE = "https://meetings-eu1.hubspot.com"
SLUG = "dennis-kwiatkowski"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


def line(c="="):
    print(c * 70)


def fetch(url, accept=None):
    h = dict(HEADERS)
    if accept:
        h["Accept"] = accept
    h["Referer"] = f"{BASE}/{SLUG}"
    h["Origin"] = BASE
    return requests.get(url, headers=h, timeout=30)


def main():
    page_url = f"{BASE}/{SLUG}"
    line()
    print(f"GET {page_url}")
    r = fetch(page_url, accept="text/html")
    html = r.text
    print(f"status={r.status_code} content-type={r.headers.get('content-type')} len={len(html)}")

    # 1) Embedded JSON script blocks
    line("-")
    print("Embedded <script type=application/json> blocks:")
    for m in re.finditer(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', html, re.S):
        block = m.group(1).strip()
        print(f"  [block len={len(block)}] head: {block[:500]}")

    # 2) Keyword hits with context
    line("-")
    for kw in ["linkAvailability", "availabilityByDuration", "portalId", "api/booking",
               "scheduler/", "availability", "meetingsUuid", "linkId", "/api/"]:
        idxs = [m.start() for m in re.finditer(re.escape(kw), html)]
        print(f"keyword {kw!r}: {len(idxs)} hit(s)")
        for i in idxs[:3]:
            print(f"    ...{html[max(0,i-60):i+80]!r}...")

    # 3) Candidate API URLs found in HTML
    line("-")
    urls = set(re.findall(r'https?://[^\s"\'<>]*(?:booking|scheduler|availabilit|meetings)[^\s"\'<>]*', html))
    print(f"candidate URLs in HTML ({len(urls)}):")
    for u in sorted(urls)[:40]:
        print(f"    {u}")

    # 4) Probe candidate endpoints
    line()
    print("Probing candidate JSON endpoints:")
    candidates = [
        f"{BASE}/api/booking/v1/meetings/{SLUG}",
        f"{BASE}/api/booking/v1/meeting/{SLUG}",
        f"{BASE}/api/booking/v1/availability/{SLUG}",
        f"{BASE}/api/booking/v1/meetings/availability/{SLUG}",
        f"{BASE}/api/booking/v1/widget/availability/{SLUG}",
        f"{BASE}/api/booking/v1/meetings/book/{SLUG}",  # json-only Accept
    ]
    for url in candidates:
        try:
            rr = fetch(url, accept="application/json")
            ct = rr.headers.get("content-type", "")
            body = rr.text[:200].replace("\n", " ")
            is_json = "json" in ct or body.lstrip().startswith(("{", "["))
            print(f"  [{rr.status_code} {ct.split(';')[0]} json={is_json}] {url}")
            print(f"      body: {body!r}")
        except Exception as exc:  # noqa
            print(f"  [ERR] {url}: {exc}")


if __name__ == "__main__":
    main()
