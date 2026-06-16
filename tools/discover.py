"""One-shot endpoint discovery (run in CI, where HubSpot is reachable).

The meetings page is a pure SPA; the availability endpoint is constructed inside
the JS bundle. This script fetches the page, pulls every referenced script, and
greps the bundles for API path fragments so we can identify the real endpoint.
"""
from __future__ import annotations

import re

import requests

BASE = "https://meetings-eu1.hubspot.com"
SLUG = "dennis-kwiatkowski"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": f"{BASE}/{SLUG}",
    "Origin": BASE,
}

KEYWORDS = [
    "availability", "available", "booking", "scheduler", "meeting-links",
    "meetingsBook", "linkAvailability", "/api/", "monthOffset", "freeBusy",
]


def get(url):
    return requests.get(url, headers=HEADERS, timeout=30)


def grep(text, label):
    found = False
    for kw in KEYWORDS:
        for m in re.finditer(re.escape(kw), text):
            found = True
            i = m.start()
            snippet = text[max(0, i - 90):i + 110].replace("\n", " ")
            print(f"  [{label}] {kw!r}: ...{snippet!r}...")
            break  # one example per keyword per file
    return found


def main():
    page = get(f"{BASE}/{SLUG}")
    html = page.text
    print(f"page status={page.status_code} len={len(html)}")

    # All script srcs and any absolute URLs to JS.
    srcs = set(re.findall(r'<script[^>]+src="([^"]+)"', html))
    srcs |= set(re.findall(r'"(https://[^"]+\.js[^"]*)"', html))
    # Resolve protocol-relative / relative URLs.
    resolved = []
    for s in srcs:
        if s.startswith("//"):
            resolved.append("https:" + s)
        elif s.startswith("http"):
            resolved.append(s)
        elif s.startswith("/"):
            resolved.append(BASE + s)
    resolved = sorted(set(resolved))
    print(f"\nfound {len(resolved)} script url(s):")
    for s in resolved:
        print(f"  {s}")

    # Also extract all path-ish strings from inline HTML that mention keywords.
    print("\n--- inline HTML keyword scan ---")
    grep(html, "html")

    # Fetch each bundle and scan it.
    print("\n--- bundle scans ---")
    api_paths = set()
    for url in resolved:
        try:
            r = get(url)
            body = r.text
            print(f"\n# {url}  (status={r.status_code} len={len(body)})")
            grep(body, "js")
            # Capture concrete path fragments mentioning the keywords.
            for m in re.finditer(r'["\'`](/[A-Za-z0-9/_\-.{}$]*(?:availab|booking|scheduler|meeting-links)[A-Za-z0-9/_\-.{}$]*)["\'`]', body):
                api_paths.add(m.group(1))
            for m in re.finditer(r'(https://[A-Za-z0-9.\-]+/[A-Za-z0-9/_\-.{}$]*(?:availab|booking|scheduler|meeting-links)[A-Za-z0-9/_\-.{}$]*)', body):
                api_paths.add(m.group(1))
        except Exception as exc:  # noqa
            print(f"\n# {url}  ERROR {exc}")

    print("\n=== candidate API path fragments ===")
    for p in sorted(api_paths):
        print(f"  {p}")


if __name__ == "__main__":
    main()
