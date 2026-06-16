"""Probe regional API hosts for the meetings-public availability endpoint."""
from __future__ import annotations

import json
import requests

SLUG = "dennis-kwiatkowski"
TZ = "Europe/Berlin"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": f"https://meetings-eu1.hubspot.com/{SLUG}",
    "Origin": "https://meetings-eu1.hubspot.com",
}

AVAIL_QS = f"slug={SLUG}&monthOffset=0&timezone={TZ}"
HOSTS = [
    "https://api-eu1.hubspot.com",
    "https://api-eu1.hubapi.com",
    "https://api.hubapi.com",
    "https://api.hubspot.com",
]
URLS = []
for h in HOSTS:
    URLS.append(f"{h}/meetings-public/v3/book/availability-page?{AVAIL_QS}")
    URLS.append(f"{h}/meetings-public/v3/book/book-info?slug={SLUG}")


def summarize(obj, prefix="", depth=0, lines=None):
    if lines is None:
        lines = []
    if depth > 4 or len(lines) > 80:
        return lines
    if isinstance(obj, dict):
        for k, v in obj.items():
            t = type(v).__name__
            extra = f" len={len(v)}" if isinstance(v, (list, dict)) else f" = {v!r}"[:70]
            lines.append(f"{prefix}{k}: {t}{extra}")
            if isinstance(v, (dict, list)):
                summarize(v, prefix + "  ", depth + 1, lines)
    elif isinstance(obj, list) and obj:
        lines.append(f"{prefix}[0] of {len(obj)}:")
        summarize(obj[0], prefix + "  ", depth + 1, lines)
    return lines


def main():
    for url in URLS:
        print("=" * 70)
        print("GET", url)
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            ct = r.headers.get("content-type", "")
            print(f"status={r.status_code} content-type={ct} len={len(r.text)}")
            if "json" in ct or r.text.lstrip().startswith(("{", "[")):
                data = r.json()
                if r.status_code == 200:
                    print("--- structure ---")
                    for ln in summarize(data):
                        print(ln)
                    print("--- raw head (2500) ---")
                    print(json.dumps(data)[:2500])
                else:
                    print("json error:", json.dumps(data)[:200])
            else:
                print("HTML/other body head:", r.text[:120])
        except Exception as exc:  # noqa
            print("ERROR", exc)


if __name__ == "__main__":
    main()
