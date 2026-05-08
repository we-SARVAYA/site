"""Rebuild the `## Blog Articles` section of llms.txt from the current
state of blog/*.html. Use to re-sync if the publisher's incremental
update was skipped (manual blog edits, crashes, drift).

Reads each post's "headline" from JSON-LD or <title>, sorts by
"datePublished" descending, rewrites the article list section, and
bumps the trailing "Last updated" line to today.

Run any time: idempotent - same input produces same output.
"""
from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BLOG_DIR = ROOT / "blog"
LLMS = ROOT / "llms.txt"

ARTICLES_HEADING = "## Blog Articles"


def collect() -> list[dict]:
    posts = []
    for p in sorted(BLOG_DIR.glob("*.html")):
        text = p.read_text(encoding="utf-8")
        headline_m = re.search(r'"headline":\s*"([^"]+)"', text)
        date_m = re.search(r'"datePublished":\s*"([^"]+)"', text)
        title_m = re.search(r"<title>([^|]+)\|", text)
        title = (
            headline_m.group(1)
            if headline_m
            else (title_m.group(1).strip() if title_m else p.stem)
        )
        posts.append({
            "slug": p.stem,
            "title": title,
            "date": date_m.group(1) if date_m else "",
        })
    posts.sort(key=lambda x: x["date"])  # ascending; oldest first like existing layout
    return posts


def main() -> int:
    posts = collect()
    text = LLMS.read_text(encoding="utf-8")

    section_re = re.compile(
        rf"({re.escape(ARTICLES_HEADING)}\n\n)(.*?)(\n\n## )",
        re.S,
    )
    m = section_re.search(text)
    if not m:
        sys.exit(f"Could not find '{ARTICLES_HEADING}' section in llms.txt")

    new_list = "\n".join(
        f"- [{p['title']}](https://sarvaya.in/blog/{p['slug']})" for p in posts
    )
    new_section = m.group(1) + new_list + m.group(3)
    text = text[:m.start()] + new_section + text[m.end():]

    text = re.sub(
        r"> Last updated: \d{4}-\d{2}-\d{2}",
        f"> Last updated: {date.today().isoformat()}",
        text,
    )

    LLMS.write_text(text, encoding="utf-8")
    print(f"Rewrote {len(posts)} blog entries; bumped Last updated to {date.today().isoformat()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
