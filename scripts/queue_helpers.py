#!/usr/bin/env python3
"""Helpers for the blog post queue. Run during refill sessions only.

Subcommands:
  gen-images     Iterate manifest, generate WebP hero images via Gemini for
                 any queued post that doesn't already have one.
  gen-image SLUG Generate the WebP image for a single queued slug.
  validate       Sanity-check manifest entries against files in posts/.

Requires GEMINI_API_KEY in env.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import sys
import time
from pathlib import Path

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
QUEUE_DIR = Path(__file__).resolve().parent / "post_queue"
QUEUE_POSTS = QUEUE_DIR / "posts"
MANIFEST = QUEUE_DIR / "manifest.json"
IMAGES_DIR = ROOT / "assets" / "images" / "blog"
THUMBNAIL_STYLE_FILE = Path(__file__).resolve().parent / "thumbnail_style.md"

GEMINI_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")

STYLE_REFERENCE_IMAGES = [
    "blog-storytelling.webp",
    "blog-ux.webp",
    "blog-website.webp",
    "blog-seo.webp",
    "blog-app.webp",
    "blog-whitelabel.webp",
    "blog-ai.webp",
]


def _is_on_brand_pixel(r: int, g: int, b: int) -> bool:
    if max(r, g, b) < 40:
        return True
    if g >= 140 and r >= 120 and b < 130 and g > b + 50 and g >= r - 30:
        return True
    if (max(r, g, b) - min(r, g, b)) <= 35 and r >= b - 5:
        return True
    return False


def _off_brand_ratio(img: "Image.Image") -> float:
    small = img.resize((120, 68), Image.LANCZOS)
    pixels = list(small.getdata())
    foreground = [(r, g, b) for r, g, b in pixels if max(r, g, b) >= 40]
    if not foreground:
        return 1.0
    off = sum(1 for r, g, b in foreground if not _is_on_brand_pixel(r, g, b))
    return off / len(foreground)


def _gemini_call(parts: list) -> "Image.Image":
    api_key = os.environ["GEMINI_API_KEY"]
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={api_key}"
    )
    body = {"contents": [{"parts": parts}]}
    r = requests.post(url, json=body, timeout=180)
    if r.status_code != 200:
        raise RuntimeError(f"Gemini error {r.status_code}: {r.text[:800]}")
    data = r.json()
    for candidate in data.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                img_bytes = base64.b64decode(inline["data"])
                img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                img = img.resize((1200, 675), Image.LANCZOS)
                return img
    raise RuntimeError(f"No inline image in Gemini response:\n{json.dumps(data)[:800]}")


def _encode_webp(img: "Image.Image") -> bytes:
    buf = io.BytesIO()
    img.save(buf, "WEBP", quality=85, method=6)
    return buf.getvalue()


def _build_prompt(thumbnail_prompt: str) -> str:
    style_rules = THUMBNAIL_STYLE_FILE.read_text(encoding="utf-8")
    n_refs = sum(1 for n in STYLE_REFERENCE_IMAGES if (IMAGES_DIR / n).exists())
    return f"""NO TEXT. NO LETTERS. NO WORDS. NO NUMBERS. NO SYMBOLS THAT LOOK LIKE LETTERS.

This is the SINGLE MOST IMPORTANT RULE. Study these example violations and do NOT produce anything similar:
- A box labeled "P" or "G" = FAILURE (contains a letter)
- A page with "ABC" or squiggle-text that reads as words = FAILURE
- Any character that could be confused with a letter, number, or punctuation = FAILURE

If you are tempted to put ANY character inside any shape, STOP. Use abstract geometric shapes (circle, square, triangle, star), dots, or stripes instead, or leave the shape empty.

Generate a blog thumbnail matching the visual style of the {n_refs} reference images attached.

ALLOWED COLORS - ONLY these three:
1. Pure black (#000000) background
2. Warm off-white / bone color for ALL line work (same color everywhere)
3. ONE single shape filled with solid lime green (#C8FF00)

BANNED COLORS - do not use ANY of these anywhere in the image:
- NO blue, cyan, teal, navy
- NO purple, violet, magenta, pink
- NO red, orange, yellow, gold
- NO green other than the single lime-green accent shape
- NO gradients, NO color fades, NO color glows
- NO multicolor lines - every line must be the SAME warm off-white

BANNED COMPOSITION:
- NO 3D rendering, perspective grids, vanishing points, or depth
- NO photography, realism, drop shadows, or lighting effects
- NO frame or border

STYLE GUIDE:
{style_rules}

SUBJECT (depict ABSTRACTLY with shapes, never with labels or named logos):
{thumbnail_prompt}

Reproduce the attached references' style exactly: pure black background, warm off-white grainy hand-drawn lines (all the same color), ONE green filled shape, small 4-point sparkles and dots in the negative space, flat 2D, NOTHING readable as text anywhere."""


def generate_image_for_slug(slug: str, thumbnail_prompt: str) -> bytes:
    reference_parts = []
    for name in STYLE_REFERENCE_IMAGES:
        ref_path = IMAGES_DIR / name
        if ref_path.exists():
            b64 = base64.b64encode(ref_path.read_bytes()).decode()
            reference_parts.append(
                {"inlineData": {"mimeType": "image/webp", "data": b64}}
            )
    parts = reference_parts + [{"text": _build_prompt(thumbnail_prompt)}]

    acceptable_ratio = 0.30
    max_attempts = 5
    last_err = None
    best_img = None
    best_ratio = 1.0

    for attempt in range(1, max_attempts + 1):
        try:
            img = _gemini_call(parts)
            ratio = _off_brand_ratio(img)
            print(f"  [{slug}] attempt {attempt}: off-brand foreground = {ratio:.1%}", flush=True)
            if ratio < best_ratio:
                best_ratio, best_img = ratio, img
            if ratio <= acceptable_ratio:
                return _encode_webp(img)
        except Exception as e:  # noqa: BLE001
            last_err = e
            print(f"  [{slug}] attempt {attempt} failed: {e}; retrying", flush=True)
            time.sleep(3)

    if last_err is not None and best_img is None:
        raise RuntimeError(f"Image generation failed after {max_attempts} attempts: {last_err}")
    raise RuntimeError(
        f"[{slug}] off-brand ratio {best_ratio:.1%} exceeded acceptable "
        f"{acceptable_ratio:.0%} across {max_attempts} attempts."
    )


def cmd_gen_images(args: argparse.Namespace) -> int:
    if not os.environ.get("GEMINI_API_KEY"):
        sys.exit("GEMINI_API_KEY not set")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    targets = []
    for entry in manifest.get("posts", []):
        if entry.get("status") != "queued":
            continue
        slug = entry["slug"]
        if (QUEUE_POSTS / f"{slug}.webp").exists():
            continue
        if "thumbnail_prompt" not in entry:
            print(f"  [{slug}] SKIP: no thumbnail_prompt in manifest", flush=True)
            continue
        targets.append(entry)

    if not targets:
        print("No images to generate.", flush=True)
        return 0

    print(f"Generating {len(targets)} image(s)...", flush=True)
    failures = []
    for entry in targets:
        slug = entry["slug"]
        try:
            data = generate_image_for_slug(slug, entry["thumbnail_prompt"])
            (QUEUE_POSTS / f"{slug}.webp").write_bytes(data)
            print(f"  [{slug}] -> {len(data):,} bytes", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"  [{slug}] FAILED: {e}", flush=True)
            failures.append(slug)

    if failures:
        print(f"\n{len(failures)} failure(s): {failures}", flush=True)
        return 1
    print("\nAll images generated.", flush=True)
    return 0


def cmd_gen_image(args: argparse.Namespace) -> int:
    if not os.environ.get("GEMINI_API_KEY"):
        sys.exit("GEMINI_API_KEY not set")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entry = next((e for e in manifest.get("posts", []) if e.get("slug") == args.slug), None)
    if entry is None:
        sys.exit(f"slug not found in manifest: {args.slug}")
    if "thumbnail_prompt" not in entry:
        sys.exit(f"no thumbnail_prompt in manifest entry for {args.slug}")
    data = generate_image_for_slug(args.slug, entry["thumbnail_prompt"])
    (QUEUE_POSTS / f"{args.slug}.webp").write_bytes(data)
    print(f"Wrote {len(data):,} bytes to {QUEUE_POSTS / f'{args.slug}.webp'}", flush=True)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    problems: list[str] = []
    seen_slugs: set[str] = set()
    required_fields = {"slug", "title", "tag", "excerpt", "thumbnail_prompt", "status"}

    for i, entry in enumerate(manifest.get("posts", [])):
        prefix = f"posts[{i}]"
        missing = required_fields - entry.keys()
        if missing:
            problems.append(f"{prefix}: missing fields {sorted(missing)}")
            continue
        slug = entry["slug"]
        if slug in seen_slugs:
            problems.append(f"{prefix}: duplicate slug {slug}")
        seen_slugs.add(slug)
        if entry["status"] != "queued":
            continue
        html_path = QUEUE_POSTS / f"{slug}.html"
        img_path = QUEUE_POSTS / f"{slug}.webp"
        if not html_path.exists():
            problems.append(f"{prefix}: missing {html_path.name}")
        else:
            text = html_path.read_text(encoding="utf-8")
            if "<!DOCTYPE html" not in text:
                problems.append(f"{prefix}: {html_path.name} missing <!DOCTYPE html>")
            if "{{PUBLISH_DATE}}" not in text:
                problems.append(f"{prefix}: {html_path.name} has no {{PUBLISH_DATE}} token")
            if f"blog-{slug}.webp" not in text:
                problems.append(f"{prefix}: {html_path.name} doesn't reference blog-{slug}.webp")
        if not img_path.exists():
            problems.append(f"{prefix}: missing {img_path.name}")

    if problems:
        print(f"FAIL: {len(problems)} problem(s):", flush=True)
        for p in problems:
            print(f"  - {p}", flush=True)
        return 1
    queued = sum(1 for e in manifest.get("posts", []) if e.get("status") == "queued")
    print(f"OK: {queued} queued post(s) validated.", flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("gen-images", help="Generate images for all queued posts missing one")
    p_one = sub.add_parser("gen-image", help="Generate image for one slug")
    p_one.add_argument("slug")
    sub.add_parser("validate", help="Sanity-check manifest and post files")
    args = parser.parse_args()

    if args.cmd == "gen-images":
        return cmd_gen_images(args)
    if args.cmd == "gen-image":
        return cmd_gen_image(args)
    if args.cmd == "validate":
        return cmd_validate(args)
    parser.error(f"Unknown command {args.cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
