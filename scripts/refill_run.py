#!/usr/bin/env python3
"""One-shot runner for /refill-blog-queue sessions.

Reads every JSON spec in scripts/post_queue/specs/, runs them through
build_post.build_post(), writes the HTML to scripts/post_queue/posts/,
and rewrites scripts/post_queue/manifest.json with all queued entries
in spec-file order.

Run AFTER all 14 spec JSONs are written. Then run:
    python scripts/queue_helpers.py validate
    python scripts/queue_helpers.py gen-images
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC_DIR = Path(__file__).resolve().parent / "post_queue" / "specs"
POST_DIR = Path(__file__).resolve().parent / "post_queue" / "posts"
MANIFEST = Path(__file__).resolve().parent / "post_queue" / "manifest.json"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_post import build_post

BANNED_PHRASES = [
    "delve", "leverage", "utilize", "utilise", "tapestry", "unleash",
    "realm", "dive in", "dive into", "in today's world", "in the digital age",
    "revolutionize", "revolutionise", "game-changer", "game changer",
    "cutting-edge", "seamless", "synergy", "paradigm", "holistic", "empower",
    "pivotal", "foster", "embark", "harness", "spearhead", "elevate",
    "bespoke", "meticulous", "testament", "ever-evolving", "transformative",
    "thought leader", "supercharge", "at the forefront", "plethora", "myriad",
    "it's not just", "it is not just", "more than just", "in a world where",
    "let's explore", "let's dive", "let's take a look", "in conclusion",
    "to sum up", "at the end of the day", "it's worth noting",
    "it is important to note", "it goes without saying", "needless to say",
    "streamline", "ecosystem ", "deep dive", "navigate the",
]


def main() -> int:
    spec_files = sorted(SPEC_DIR.glob("*.json"))
    if not spec_files:
        sys.exit("No spec files found in scripts/post_queue/specs/")

    POST_DIR.mkdir(parents=True, exist_ok=True)
    queued = []
    now_iso = datetime.now(timezone.utc).isoformat()
    banlist_failures: list[tuple[str, list[str]]] = []

    for spec_path in spec_files:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        body_lower = spec["body_html"].lower()
        hits = [w for w in BANNED_PHRASES if w in body_lower]
        if hits:
            banlist_failures.append((spec["slug"], hits))
            continue

        html = build_post(spec)
        out = POST_DIR / f"{spec['slug']}.html"
        out.write_text(html, encoding="utf-8")
        print(f"  built {out.name} ({len(html):,} bytes)")

        queued.append({
            "slug": spec["slug"],
            "title": spec["title"],
            "tag": spec["tag"],
            "excerpt": spec["excerpt"],
            "category": spec.get("category", spec["article_section"]),
            "thumbnail_prompt": spec["thumbnail_prompt"],
            "queued_at": now_iso,
            "published_at": None,
            "status": "queued",
        })

    if banlist_failures:
        print("\nFAIL: banlist hits in the following specs:")
        for slug, hits in banlist_failures:
            print(f"  {slug}: {hits}")
        return 1

    MANIFEST.write_text(json.dumps({"posts": queued}, indent=2) + "\n", encoding="utf-8")
    print(f"\nManifest written: {len(queued)} queued post(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
