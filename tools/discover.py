"""One-shot endpoint probe: hit the real availability-page endpoint variants
and dump JSON structure so we can finalize the parser.
"""
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

QS = f"slug={SLUG}&monthOffset=0&timezone={TZ}"
CANDIDATES = [
    f"https://meetings-eu1.hubspot.com/api/meetings-public/v3/book/availability-page?{QS}",
    f"https://meetings-eu1.hubspot.com/meetings-public/v3/book/availability-page?{QS}",
    f"https://api.hubspot.com/meetings-public/v3/book/availability-page?{QS}",
    f"https://meetings-eu1.hubspot.com/api/meetings-public/v3/book/book-info?slug={SLUG}",
]


def summarize(obj, prefix="", depth=0, lines=None):
    if lines is None:
        lines = []
    if depth > 3 or len(lines) > 60:
        return lines
    if isinstance(obj, dict):
        for k, v in obj.items():
            t = type(v).__name__
            extra = f" len={len(v)}" if isinstance(v, (list, dict)) else f" = {v!r}"[:60]
            lines.append(f"{prefix}{k}: {t}{extra}")
            if isinstance(v, (dict, list)):
                summarize(v, prefix + "  ", depth + 1, lines)
    elif isinstance(obj, list) and obj:
        lines.append(f"{prefix}[0] of {len(obj)}:")
        summarize(obj[0], prefix + "  ", depth + 1, lines)
    return lines


def main():
    for url in CANDIDATES:
        print("=" * 70)
        print("GET", url)
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            ct = r.headers.get("content-type", "")
            print(f"status={r.status_code} content-type={ct} len={len(r.text)}")
            if "json" in ct or r.text.lstrip().startswith(("{", "[")):
                data = r.json()
                print("--- structure ---")
                for ln in summarize(data):
                    print(ln)
                print("--- raw head (1500) ---")
                print(json.dumps(data)[:1500])
            else:
                print("body head:", r.text[:160])
        except Exception as exc:  # noqa
            print("ERROR", exc)


if __name__ == "__main__":
    main()
