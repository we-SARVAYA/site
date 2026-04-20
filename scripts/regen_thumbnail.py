"""One-off: regenerate a single blog thumbnail by slug.

Usage: python scripts/regen_thumbnail.py <slug> "<thumbnail prompt>"
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_blog import generate_thumbnail, IMAGES_DIR  # noqa: E402


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    slug, prompt = sys.argv[1], sys.argv[2]
    topic = {"slug": slug, "thumbnail_prompt": prompt}
    webp = generate_thumbnail(topic)
    out = IMAGES_DIR / f"blog-{slug}.webp"
    out.write_bytes(webp)
    print(f"wrote {out} ({len(webp)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
