#!/usr/bin/env python3
"""Publish the next queued blog post.

Reads scripts/post_queue/manifest.json, finds the first post with
status="queued", copies its HTML + image into the live site, patches
blog.html / index.html / sitemap.xml / llms.txt, marks the entry as
published, and updates topics_log.json.

No LLM calls. No external API dependencies. If the queue is empty,
exits with a warning instead of failing.

Refill the queue weekly by running the /refill-blog-queue Claude Code
slash command (see scripts/post_queue/REFILL_GUIDE.md).
"""
from __future__ import annotations

import html
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BLOG_DIR = ROOT / "blog"
IMAGES_DIR = ROOT / "assets" / "images" / "blog"
BLOG_INDEX = ROOT / "blog.html"
HOME_INDEX = ROOT / "index.html"
SITEMAP = ROOT / "sitemap.xml"
LLMS = ROOT / "llms.txt"
TOPICS_LOG = Path(__file__).resolve().parent / "topics_log.json"

QUEUE_DIR = Path(__file__).resolve().parent / "post_queue"
QUEUE_POSTS = QUEUE_DIR / "posts"
QUEUE_ARCHIVE = QUEUE_DIR / "archive"
MANIFEST = QUEUE_DIR / "manifest.json"


CARD_TEMPLATE = """
                <article class="blog-card">
                    <div class="blog-card__img">
                        <img src="{img_src}" alt="{title_attr}" loading="lazy" width="400" height="240">
                    </div>
                    <div class="blog-card__body">
                        <div class="blog-meta">
                            <span class="blog-tag">{tag}</span>
                            <time class="blog-date" datetime="{date}">{date_human}</time>
                        </div>
                        <h3 class="blog-title">{title_text}</h3>
                        <a href="blog/{slug}" class="blog-link">Read Article
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="7" y1="17" x2="17" y2="7"></line><polyline points="7 7 17 7 17 17"></polyline></svg>
                        </a>
                    </div>
                </article>
"""


FEATURED_TEMPLATE = """<article class="blog-featured">
                <div class="blog-featured__img">
                    <img src="assets/images/blog/blog-{slug}.webp" alt="{title_attr}" loading="eager" width="720" height="400">
                </div>
                <div class="blog-featured__content">
                    <div class="blog-featured__meta">
                        <span class="blog-tag">{tag}</span>
                        <time datetime="{date}">{date_human}</time>
                    </div>
                    <h2 class="blog-featured__title">{title_text}</h2>
                    <p class="blog-featured__excerpt">{excerpt}</p>
                    <a href="blog/{slug}" class="blog-featured__link">Read Article
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>
                    </a>
                </div>
            </article>"""


def _extract_featured_fields(featured_html: str) -> dict | None:
    img_m = re.search(r'<img\s+src="([^"]+)"\s+alt="([^"]+)"', featured_html)
    href_m = re.search(r'<a href="blog/([^"]+)"', featured_html)
    tag_m = re.search(r'<span class="blog-tag">([^<]+)</span>', featured_html)
    time_m = re.search(r'<time datetime="([^"]+)">([^<]+)</time>', featured_html)
    title_m = re.search(r'<h2 class="blog-featured__title">([^<]+)</h2>', featured_html)
    if not all([img_m, href_m, tag_m, time_m, title_m]):
        return None
    return {
        "img_src": img_m.group(1),
        "title_attr": img_m.group(2),
        "slug": href_m.group(1),
        "tag": tag_m.group(1),
        "datetime": time_m.group(1),
        "date_human": time_m.group(2),
        "title_text": title_m.group(1),
    }


def _insert_card_chronologically(text: str, card_html: str, card_datetime: str) -> str:
    marker = '<!-- All Posts -->\n            <div class="blog-grid">\n'
    if marker not in text:
        raise RuntimeError("blog.html grid marker not found")
    grid_start = text.find(marker) + len(marker)
    card_pattern = re.compile(r'<article class="blog-card">.*?</article>', re.DOTALL)
    for m in card_pattern.finditer(text, pos=grid_start):
        dt_m = re.search(r'<time class="blog-date" datetime="([^"]+)"', m.group(0))
        if dt_m and dt_m.group(1) <= card_datetime:
            insert_at = m.start()
            line_start = text.rfind("\n", 0, insert_at) + 1
            return text[:line_start] + card_html.lstrip("\n") + "\n" + text[line_start:]
    return text.replace(marker, marker + card_html, 1)


def _latest_posts_from_blog_index(blog_index_html: str, n: int = 3) -> list[dict]:
    posts: list[dict] = []
    feat_match = re.search(
        r'<article class="blog-featured">.*?</article>', blog_index_html, re.DOTALL
    )
    if feat_match:
        f = _extract_featured_fields(feat_match.group(0))
        if f:
            posts.append(f)

    grid_marker = '<!-- All Posts -->\n            <div class="blog-grid">\n'
    grid_pos = blog_index_html.find(grid_marker)
    if grid_pos != -1:
        for m in re.finditer(
            r'<article class="blog-card">.*?</article>',
            blog_index_html[grid_pos:],
            re.DOTALL,
        ):
            if len(posts) >= n:
                break
            card = m.group(0)
            img_m = re.search(r'<img\s+src="([^"]+)"\s+alt="([^"]+)"', card)
            href_m = re.search(r'<a href="blog/([^"]+)"', card)
            tag_m = re.search(r'<span class="blog-tag">([^<]+)</span>', card)
            time_m = re.search(
                r'<time class="blog-date" datetime="([^"]+)">([^<]+)</time>', card
            )
            title_m = re.search(r'<h3 class="blog-title">([^<]+)</h3>', card)
            if all([img_m, href_m, tag_m, time_m, title_m]):
                posts.append({
                    "img_src": img_m.group(1),
                    "slug": href_m.group(1),
                    "tag": tag_m.group(1),
                    "datetime": time_m.group(1),
                    "date_human": time_m.group(2),
                    "title_text": title_m.group(1),
                    "title_attr": img_m.group(2),
                })
    return posts[:n]


def patch_home_blog_section(latest_posts: list[dict]) -> str:
    text = HOME_INDEX.read_text(encoding="utf-8")
    section_re = re.compile(
        r'(<h2 class="section-title">Our Blogs</h2>\s*\n\s*<div class="blog-grid">\n)'
        r'(.*?)'
        r'(\n            </div>\s*\n\s*</div>\s*\n\s*</section>)',
        re.DOTALL,
    )
    m = section_re.search(text)
    if not m:
        raise RuntimeError("index.html 'Our Blogs' section not found")

    cards_html = ""
    for p in latest_posts:
        cards_html += CARD_TEMPLATE.format(
            img_src=p["img_src"],
            slug=p["slug"],
            title_text=p["title_text"],
            title_attr=p["title_attr"],
            tag=p["tag"],
            date=p["datetime"],
            date_human=p["date_human"],
        )
    return text[:m.start(2)] + cards_html.lstrip("\n").rstrip("\n") + text[m.end(2):]


def patch_blog_index(topic: dict, today: str, date_human: str) -> str:
    text = BLOG_INDEX.read_text(encoding="utf-8")
    featured_match = re.search(
        r'<article class="blog-featured">.*?</article>', text, re.DOTALL
    )
    if not featured_match:
        raise RuntimeError("blog.html featured block not found")
    fields = _extract_featured_fields(featured_match.group(0))
    if fields is None:
        raise RuntimeError("could not parse current featured block")

    new_featured = FEATURED_TEMPLATE.format(
        slug=topic["slug"],
        title_text=html.escape(topic["title"]),
        title_attr=html.escape(topic["title"], quote=True),
        excerpt=html.escape(topic["excerpt"]),
        tag=html.escape(topic["tag"]),
        date=today,
        date_human=date_human,
    )
    text = text[:featured_match.start()] + new_featured + text[featured_match.end():]

    if re.search(rf'<a href="blog/{re.escape(fields["slug"])}" class="blog-link"', text):
        return text

    demoted_card = CARD_TEMPLATE.format(
        img_src=fields["img_src"],
        slug=fields["slug"],
        title_text=fields["title_text"],
        title_attr=fields["title_attr"],
        tag=fields["tag"],
        date=fields["datetime"],
        date_human=fields["date_human"],
    )
    return _insert_card_chronologically(text, demoted_card, fields["datetime"])


def patch_sitemap(topic: dict, today: str) -> str:
    text = SITEMAP.read_text(encoding="utf-8")
    entry = (
        "    <url>\n"
        f"        <loc>https://sarvaya.in/blog/{topic['slug']}</loc>\n"
        f"        <lastmod>{today}</lastmod>\n"
        "        <changefreq>monthly</changefreq>\n"
        "        <priority>0.6</priority>\n"
        "    </url>\n"
    )
    return text.replace("</urlset>", entry + "</urlset>")


def patch_llms(topic: dict) -> str:
    text = LLMS.read_text(encoding="utf-8")
    new_line = f"- [{topic['title']}](https://sarvaya.in/blog/{topic['slug']})"
    lines = text.split("\n")
    last_idx = -1
    for i, ln in enumerate(lines):
        if ln.startswith("- [") and "/blog/" in ln:
            last_idx = i
    if last_idx != -1:
        lines.insert(last_idx + 1, new_line)
        return "\n".join(lines)
    if text and not text.endswith("\n"):
        text += "\n"
    return text + new_line + "\n"


def load_manifest() -> dict:
    if not MANIFEST.exists():
        return {"posts": []}
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def save_manifest(data: dict) -> None:
    MANIFEST.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def load_topics_log() -> list[dict]:
    if TOPICS_LOG.exists():
        return json.loads(TOPICS_LOG.read_text(encoding="utf-8"))
    return []


def pick_next_queued(manifest: dict) -> dict | None:
    for entry in manifest.get("posts", []):
        if entry.get("status") == "queued":
            return entry
    return None


def existing_blog_slugs() -> set[str]:
    return {p.stem for p in BLOG_DIR.glob("*.html")}


def main() -> int:
    manifest = load_manifest()
    entry = pick_next_queued(manifest)
    if entry is None:
        msg = "Queue is empty. Run /refill-blog-queue to add posts."
        print(f"[publish_next] {msg}", flush=True)
        gh_out = os.environ.get("GITHUB_OUTPUT")
        if gh_out:
            with open(gh_out, "a", encoding="utf-8") as f:
                f.write("queue_empty=true\n")
        return 0

    slug = entry["slug"]
    if slug in existing_blog_slugs():
        print(f"[publish_next] Slug {slug} already exists in blog/, marking skipped", flush=True)
        entry["status"] = "skipped"
        entry["skipped_reason"] = "slug already in blog/"
        save_manifest(manifest)
        return 0

    src_html = QUEUE_POSTS / f"{slug}.html"
    src_img = QUEUE_POSTS / f"{slug}.webp"
    if not src_html.exists():
        sys.exit(f"Queue file missing: {src_html}")
    if not src_img.exists():
        sys.exit(f"Queue image missing: {src_img}")

    today = datetime.now(timezone.utc).date().isoformat()
    date_human = datetime.strptime(today, "%Y-%m-%d").strftime("%d %B %Y")

    article_html = src_html.read_text(encoding="utf-8")
    article_html = article_html.replace("{{PUBLISH_DATE}}", today)
    article_html = article_html.replace("{{PUBLISH_DATE_HUMAN}}", date_human)

    topic = {
        "slug": slug,
        "title": entry["title"],
        "tag": entry["tag"],
        "excerpt": entry["excerpt"],
    }

    print(f"[publish_next] Publishing {slug} ({entry['title']})", flush=True)

    new_blog_index = patch_blog_index(topic, today, date_human)
    new_home_index = patch_home_blog_section(
        _latest_posts_from_blog_index(new_blog_index, n=3)
    )
    new_sitemap = patch_sitemap(topic, today)
    new_llms = patch_llms(topic)

    topics = load_topics_log()
    topics.append({
        "slug": slug,
        "title": entry["title"],
        "date": today,
        "tag": entry["tag"],
    })

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    QUEUE_ARCHIVE.mkdir(parents=True, exist_ok=True)

    (BLOG_DIR / f"{slug}.html").write_text(article_html, encoding="utf-8")
    shutil.copy2(src_img, IMAGES_DIR / f"blog-{slug}.webp")
    BLOG_INDEX.write_text(new_blog_index, encoding="utf-8")
    HOME_INDEX.write_text(new_home_index, encoding="utf-8")
    SITEMAP.write_text(new_sitemap, encoding="utf-8")
    LLMS.write_text(new_llms, encoding="utf-8")
    TOPICS_LOG.write_text(json.dumps(topics, indent=2) + "\n", encoding="utf-8")

    entry["status"] = "published"
    entry["published_at"] = datetime.now(timezone.utc).isoformat()
    save_manifest(manifest)

    shutil.move(str(src_html), str(QUEUE_ARCHIVE / f"{slug}.html"))
    shutil.move(str(src_img), str(QUEUE_ARCHIVE / f"{slug}.webp"))
    src_meta = QUEUE_POSTS / f"{slug}.json"
    if src_meta.exists():
        shutil.move(str(src_meta), str(QUEUE_ARCHIVE / f"{slug}.json"))

    remaining = sum(1 for p in manifest["posts"] if p.get("status") == "queued")
    print(f"[publish_next] Done. {remaining} post(s) remaining in queue.", flush=True)

    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as f:
            f.write(f"slug={slug}\n")
            f.write(f"title={entry['title']}\n")
            f.write(f"remaining={remaining}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
