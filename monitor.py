#!/usr/bin/env python3
"""
DC Concert Venue Monitor — cloud edition.

Runs on a schedule (e.g. via GitHub Actions), fetches four DC-area venue
listing pages, detects shows that are NEW since the last run, and sends a
push notification via ntfy. State is kept in known_shows.json, which the
workflow commits back to the repo after each run.

Standard library only — no pip install needed.

Required environment variable:
  NTFY_TOPIC   - your ntfy topic name (the thing you subscribe to in the app)
Optional:
  NTFY_SERVER  - ntfy server base URL (default: https://ntfy.sh)
"""

import json
import os
import re
import sys
import datetime
import urllib.request
import urllib.error

STATE_FILE = "known_shows.json"
LOG_FILE = "new_shows_log.md"

NTFY_SERVER = (os.environ.get("NTFY_SERVER") or "https://ntfy.sh").rstrip("/")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC") or None

# Slugs starting with any of these are ignored (not real public concerts).
IGNORE_PREFIXES = ("private-event",)

VENUES = {
    # Patterns are path-based (no domain) so they match whether the page uses
    # absolute (https://venue.com/shows/x) or relative (/shows/x) links.
    "blackcat": {
        "name": "Black Cat",
        "url": "https://www.blackcatdc.com/schedule.html",
        "pattern": r"shows/([a-z0-9][a-z0-9-]*)\.html",
        "event_url": "https://www.blackcatdc.com/shows/{slug}.html",
    },
    "imp": {
        "name": "IMP (9:30 Club / Anthem / Lincoln / Merriweather)",
        "url": "https://impconcerts.com/",
        "pattern": r"/event/([a-z0-9][a-z0-9-]*)/",
        "event_url": "https://impconcerts.com/event/{slug}/",
    },
    "unionstage": {
        "name": "Union Stage Presents",
        "url": "https://www.unionstagepresents.com",
        "pattern": r"/shows/([a-z0-9][a-z0-9-]*)",
        "event_url": "https://www.unionstagepresents.com/shows/{slug}",
    },
    "songbyrd": {
        "name": "Songbyrd Music House",
        "url": "https://songbyrddc.com/events/",
        "pattern": r"/event/([a-z0-9][a-z0-9-]*)/",
        "event_url": "https://songbyrddc.com/event/{slug}/",
    },
}

USER_AGENT = "Mozilla/5.0 (compatible; ConcertMonitor/1.0)"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", "replace")


def slug_to_title(slug):
    """Best-effort human-readable title from a URL slug.

    Union Stage slugs end in a date token like '-28-jun'; trim it for display.
    """
    s = re.sub(r"-\d{1,2}-(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)$", "", slug)
    return s.replace("-", " ").strip().title()


def notify(title, message):
    if not NTFY_TOPIC:
        print("ERROR: NTFY_TOPIC not set; cannot send push.", file=sys.stderr)
        return
    # ntfy headers must be ASCII-safe; keep title plain. Body can be UTF-8.
    safe_title = title.encode("ascii", "ignore").decode("ascii")
    req = urllib.request.Request(
        f"{NTFY_SERVER}/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={
            "Title": safe_title,
            "Priority": "default",
            "Tags": "musical_note",
        },
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=30)
        print("Push sent.")
    except urllib.error.URLError as e:
        print(f"ERROR sending push: {e}", file=sys.stderr)


def main():
    if not os.path.exists(STATE_FILE):
        print(f"ERROR: {STATE_FILE} not found.", file=sys.stderr)
        sys.exit(1)
    with open(STATE_FILE, encoding="utf-8") as f:
        known = json.load(f)

    new_items = []          # (venue_name, title, url)
    unreachable = []

    for key, v in VENUES.items():
        known.setdefault(key, [])
        try:
            html = fetch(v["url"])
        except Exception as e:  # noqa: BLE001
            print(f"WARN: failed to fetch {key}: {e}", file=sys.stderr)
            unreachable.append(v["name"])
            continue

        found = {s.lower() for s in re.findall(v["pattern"], html, re.I)}
        if not found:
            # Site change or transient issue — do NOT wipe the baseline.
            print(f"WARN: parsed 0 shows for {key}; leaving baseline untouched.",
                  file=sys.stderr)
            unreachable.append(v["name"])
            continue

        known_set = set(known[key])
        new = sorted(
            s for s in found
            if s not in known_set and not s.startswith(IGNORE_PREFIXES)
        )
        for slug in new:
            new_items.append((v["name"], slug_to_title(slug),
                              v["event_url"].format(slug=slug)))

        # Merge everything currently listed into the baseline so each show
        # is only ever reported once (ignored slugs included, so they stay quiet).
        known[key] = sorted(known_set | found)

    # Persist baseline (always, even with no new shows — keeps it fresh).
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(known, f, indent=2)

    today = datetime.date.today().isoformat()

    if new_items:
        # Build push message
        body_lines = [f"• {title} — {venue}\n  {url}"
                      for venue, title, url in new_items]
        title = f"{len(new_items)} new show(s) at your venues"
        notify(title, "\n".join(body_lines))

        # Prepend to the human-readable log
        section = [f"## {today} — {len(new_items)} new show(s)", ""]
        by_venue = {}
        for venue, t, url in new_items:
            by_venue.setdefault(venue, []).append((t, url))
        for venue, items in by_venue.items():
            section.append(f"**{venue}**")
            for t, url in items:
                section.append(f"- {t} — {url}")
            section.append("")
        if unreachable:
            section.append(f"_Note: could not check {', '.join(unreachable)} this run._")
            section.append("")
        section.append("---")
        section.append("")
        prepend_log("\n".join(section))
        print(title)
    else:
        msg = "No new shows."
        if unreachable:
            msg += f" (Could not check: {', '.join(unreachable)}.)"
        print(msg)


def prepend_log(text):
    header = "# New Shows Log\n\nEach run prepends newly-detected shows here. Most recent at top.\n\n---\n\n"
    existing = ""
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, encoding="utf-8") as f:
            existing = f.read()
        if existing.startswith(header):
            existing = existing[len(header):]
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(header + text + existing)


if __name__ == "__main__":
    main()
