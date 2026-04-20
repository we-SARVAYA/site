#!/usr/bin/env python3
"""Auto-publish a blog post for sarvaya.in.

Pipeline:
  1. Research a trending topic via Claude CLI + WebSearch.
  2. Generate the full blog HTML via Claude CLI, copying structure from an
     existing post.
  3. Generate a hero thumbnail via Gemini 2.5 Flash Image, resize + encode WebP.
  4. Patch blog.html (insert card), sitemap.xml (insert url), llms.txt (append).
  5. Append an entry to scripts/topics_log.json.

All writes happen at the end — if any step fails, the repo is untouched.
"""
from __future__ import annotations

import base64
import html
import io
import json
import os
import random
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
BLOG_DIR = ROOT / "blog"
IMAGES_DIR = ROOT / "assets" / "images" / "blog"
BLOG_INDEX = ROOT / "blog.html"
SITEMAP = ROOT / "sitemap.xml"
LLMS = ROOT / "llms.txt"
TOPICS_LOG = Path(__file__).resolve().parent / "topics_log.json"
STYLE_FILE = Path(__file__).resolve().parent / "writing_style.md"
REFERENCE_POST = BLOG_DIR / "seo-in-2026.html"

TODAY = datetime.now(timezone.utc).date().isoformat()
DATE_HUMAN = datetime.strptime(TODAY, "%Y-%m-%d").strftime("%d %B %Y")

GEMINI_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")

# Topic categories the blog covers. Each run picks one to focus the research on,
# so the archive stays balanced instead of drifting into one niche. Order and
# weights tune how often each shows up.
TOPIC_CATEGORIES = [
    ("AEO / GEO / AI search",
     "Answer Engine Optimization, Generative Engine Optimization, Google AI Overviews, ChatGPT Search, Perplexity, Copilot, llms.txt, schema for AI citation, AI crawler policies",
     "GEO"),
    ("Claude + AI tooling",
     "Anthropic Claude product launches and new features, Claude Agent SDK, Claude Code, AI coding assistants, practical AI integrations for small businesses",
     "AI"),
    ("Traditional SEO",
     "Google algorithm updates, core updates, Core Web Vitals, technical SEO, local SEO, backlinks, on-page SEO, search ranking factors, SERP features",
     "SEO"),
    ("Web development",
     "Web performance, frameworks (Next.js, Astro, Remix), Jamstack, edge rendering, React / Vue / Svelte patterns, build tools, web standards",
     "Development"),
    ("UI / UX design",
     "Design systems, interaction patterns, accessibility, design tools (Figma), UX research, conversion design, mobile UX",
     "Design"),
    ("Brand identity + storytelling",
     "Brand strategy, logo design trends, brand storytelling, content marketing voice, brand positioning for small businesses and agencies",
     "Branding"),
    ("AI automation for business",
     "Workflow automation, no-code AI tools, Zapier / Make / n8n patterns, AI customer support, AI content ops, practical AI use cases for SMBs",
     "Automation"),
    ("Agency / white-label growth",
     "Agency business models, white-label services, client acquisition, pricing, freelancer / agency operations, productized services",
     "Agency"),
    ("App development",
     "Mobile app trends, React Native / Flutter, PWAs, app store optimization, native vs cross-platform, mobile performance",
     "Development"),
]


def load_topics() -> list[dict]:
    if TOPICS_LOG.exists():
        return json.loads(TOPICS_LOG.read_text(encoding="utf-8"))
    return []


def existing_slugs() -> set[str]:
    return {p.stem for p in BLOG_DIR.glob("*.html")}


def run_claude(prompt: str, allow_web: bool = False, timeout: int = 900) -> str:
    cmd = [
        "claude",
        "-p",
        prompt,
        "--output-format",
        "text",
        "--permission-mode",
        "bypassPermissions",
    ]
    if allow_web:
        cmd += ["--allowed-tools", "WebSearch,WebFetch"]
    else:
        # Block any file/shell tools so Claude returns text only (no side effects)
        cmd += [
            "--disallowed-tools",
            "Write,Edit,NotebookEdit,Bash,WebSearch,WebFetch,Task",
        ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(
            f"Claude CLI failed (exit {result.returncode}):\nSTDERR: {result.stderr}\nSTDOUT: {result.stdout[:500]}"
        )
    return result.stdout.strip()


def pick_category() -> tuple:
    """Return (label, description, tag) for this run.

    Uses recent topic-log history to avoid repeating the same category
    twice in a row. Falls back to random if history is thin.
    """
    topics = load_topics()
    recent_tags = [t.get("tag") for t in topics[-3:] if t.get("tag")]
    candidates = [c for c in TOPIC_CATEGORIES if c[2] not in recent_tags]
    if not candidates:
        candidates = list(TOPIC_CATEGORIES)
    return random.choice(candidates)


def research_topic(attempt: int = 1, category: tuple | None = None) -> dict:
    past = sorted({t["slug"] for t in load_topics()} | existing_slugs())
    # Cap at 120 most recent to keep the prompt bounded as the archive grows
    exclusions = "\n".join(f"- {s}" for s in past[-120:])
    if category is None:
        category = pick_category()
    cat_label, cat_desc, cat_tag = category
    tries_hint = (
        ""
        if attempt == 1
        else "\n\nIMPORTANT: your previous suggestion collided with an existing slug. Pick a distinctly DIFFERENT angle within the same category."
    )
    prompt = f"""You are a research agent for sarvaya.in, a digital agency blog covering web dev, app dev, UI/UX, SEO, AEO/GEO, AI automation, branding, and white-label agency topics.

FOCUS CATEGORY FOR THIS POST: {cat_label}
Scope: {cat_desc}

Use WebSearch to find ONE trending, newsworthy story from the past 14 days within that category. Prefer specific, actionable angles (e.g. "How the new Core Web Vitals INP threshold changes React app design") over generic evergreens ("Why UX matters"). The topic must be concrete enough that an expert could write 1200+ words with named tools, numbers, and specific techniques.

MUST NOT duplicate any of these existing slugs:
{exclusions}{tries_hint}

Output ONLY minified JSON (no markdown fences, no preamble). Schema:
{{"slug":"kebab-case-slug-max-50-chars","title":"5-14 word title","tag":"{cat_tag}","excerpt":"1-2 sentences under 160 chars","keywords":["kw1","kw2","kw3","kw4","kw5","kw6"],"thumbnail_prompt":"detailed abstract visual description for a 1200x675 hero image - no text, no logos, no named brand references"}}"""
    raw = run_claude(prompt, allow_web=True)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON found in research output:\n{raw[:1000]}")
    topic = json.loads(match.group(0))
    required = {"slug", "title", "tag", "excerpt", "keywords", "thumbnail_prompt"}
    missing = required - topic.keys()
    if missing:
        raise ValueError(f"Research JSON missing keys: {missing}")
    topic["slug"] = re.sub(r"[^a-z0-9-]", "", topic["slug"].lower().replace(" ", "-"))[:60]
    return topic


def generate_article_html(topic: dict) -> str:
    reference = REFERENCE_POST.read_text(encoding="utf-8")
    style_rules = STYLE_FILE.read_text(encoding="utf-8")
    prompt = f"""Produce a complete standalone HTML blog post for sarvaya.in.

<<<WRITING_RULES (follow EVERY rule; violation = failure)
{style_rules}
WRITING_RULES

Copy the structure of this reference post EXACTLY — every tag, class, nav
link, sidebar, script, and schema block must appear in the new post. Change
ONLY the content-specific fields (title, excerpt, dates, slug, image path,
body copy, keywords, schema values, related-post picks).

<<<REFERENCE_POST
{reference}
REFERENCE_POST

NEW POST METADATA
- slug: {topic['slug']}
- title: {topic['title']}
- tag: {topic['tag']}
- excerpt: {topic['excerpt']}
- keywords: {', '.join(topic['keywords'])}
- date: {TODAY}
- canonical: https://sarvaya.in/blog/{topic['slug']}.html
- image path in HTML: ../assets/images/blog/blog-{topic['slug']}.webp
- og:image full URL: https://sarvaya.in/assets/images/blog/blog-{topic['slug']}.webp

CONTENT REQUIREMENTS
- Write a 1200–1600 word expert article body
- Mirror the reference's heading hierarchy (h2/h3), TL;DR aside, blockquote,
  unordered lists, ordered lists, and <strong> emphasis patterns
- Confident first-person-plural voice, no filler, no "in this article we will"
- Include concrete specifics, numbers, and named tools/platforms
- Update every meta tag, og:, twitter:, canonical, JSON-LD BlogPosting,
  JSON-LD BreadcrumbList, article:published_time, article:modified_time,
  title tag, meta description, meta keywords
- The cover image <img src> must be ../assets/images/blog/blog-{topic['slug']}.webp
- For the "More from our blog" related section, pick any 3 DIFFERENT posts
  from this MANDATORY mapping. Use the image filename and title EXACTLY as
  written — do NOT invent filenames, do NOT paraphrase titles:
    * why-your-business-needs-a-website
      image: ../assets/images/blog/blog-website.webp
      title: Why Your Business Needs a Website Today
    * storytelling-in-branding
      image: ../assets/images/blog/blog-storytelling.webp
      title: The Power of Storytelling in Branding
    * importance-of-ux-designers
      image: ../assets/images/blog/blog-ux.webp
      title: The Importance of UX and Visual Designers in Successful Projects
    * white-label-growth-hack
      image: ../assets/images/blog/blog-whitelabel.webp
      title: White Label Services - The Growth Hack for Agencies
    * ai-automation-small-business
      image: ../assets/images/blog/blog-ai.webp
      title: AI Automation for Small Businesses - Where to Start
    * web-app-vs-mobile-app
      image: ../assets/images/blog/blog-app.webp
      title: Web App vs Mobile App - Which One Does Your Business Need
    * seo-in-2026
      image: ../assets/images/blog/blog-seo.webp
      title: SEO in 2026 - What Actually Works Now
- Keep all nav, sidebar share buttons, CSS/JS includes, and footer scripts
  byte-for-byte identical to the reference

OUTPUT RULES — CRITICAL
- Do NOT write files. Do NOT call any tools. Do NOT narrate.
- Do NOT explain what you did. Do NOT add preamble, summary, or markdown fences.
- Your entire response must be ONLY the raw HTML, starting with <!DOCTYPE html> and ending with </html>. Nothing before, nothing after."""
    raw = run_claude(prompt, allow_web=False, timeout=900)
    # Tolerate stray markdown fences or narration; extract the HTML block directly
    m = re.search(r"<!DOCTYPE html.*?</html>", raw, re.IGNORECASE | re.DOTALL)
    if not m:
        raise ValueError(
            f"Generated output contains no <!DOCTYPE html>...</html> block. First 600 chars:\n{raw[:600]}"
        )
    html_out = m.group(0).strip()
    # Normalize em/en dashes to the site's " - " convention site-wide.
    html_out = html_out.replace("\u2014", " - ").replace("\u2013", " - ")
    # Collapse accidental double spaces introduced by the replacement
    html_out = re.sub(r"  +", " ", html_out)
    return html_out


THUMBNAIL_STYLE_FILE = Path(__file__).resolve().parent / "thumbnail_style.md"
# Existing thumbnails used as visual style references for every generation.
# More references = stronger style lock. Only on-brand thumbnails here.
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
    """True if the pixel is close to black, warm neutral (bone/grey), or lime-green.

    Warm neutral covers the full range of grainy/textured line work from
    mid-grey shading to bone-white — any desaturated color with a slight warm
    bias (R >= B). Strong hues (teal, orange, blue, purple) fail saturation.
    """
    # Near-black background
    if max(r, g, b) < 40:
        return True
    # Lime green accent (#C8FF00 and nearby)
    if g >= 140 and r >= 120 and b < 130 and g > b + 50 and g >= r - 30:
        return True
    # Warm neutral: low saturation, warm bias (no blue cast)
    if (max(r, g, b) - min(r, g, b)) <= 35 and r >= b - 5:
        return True
    return False


def _off_brand_ratio(img: "Image.Image") -> float:
    """Off-brand fraction measured against foreground pixels only.

    Most of the frame is black background; including it dilutes contamination
    so that heavy teal/orange lines score ~5% of the whole image and slip under
    the threshold. We only count non-background (max channel >= 40) pixels.
    """
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


def generate_thumbnail(topic: dict) -> bytes:
    style_rules = THUMBNAIL_STYLE_FILE.read_text(encoding="utf-8")
    reference_parts = []
    for name in STYLE_REFERENCE_IMAGES:
        ref_path = IMAGES_DIR / name
        if ref_path.exists():
            b64 = base64.b64encode(ref_path.read_bytes()).decode()
            reference_parts.append(
                {"inlineData": {"mimeType": "image/webp", "data": b64}}
            )
    n_refs = len(reference_parts)
    prompt_text = f"""NO TEXT. NO LETTERS. NO WORDS. NO NUMBERS. NO SYMBOLS THAT LOOK LIKE LETTERS.

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
{topic['thumbnail_prompt']}

Reproduce the attached references' style exactly: pure black background, warm off-white grainy hand-drawn lines (all the same color), ONE green filled shape, small 4-point sparkles and dots in the negative space, flat 2D, NOTHING readable as text anywhere."""
    # Threshold is now measured against foreground pixels (non-background).
    # Clean on-brand thumbnails score ~15-25% (texture, anti-aliasing on lines);
    # contaminated images with teal/orange lines score 40%+.
    acceptable_ratio = 0.30
    parts = reference_parts + [{"text": prompt_text}]
    last_err = None
    best_img = None
    best_ratio = 1.0
    max_attempts = 5
    for attempt in range(1, max_attempts + 1):
        try:
            img = _gemini_call(parts)
            ratio = _off_brand_ratio(img)
            print(f"  attempt {attempt}: off-brand foreground = {ratio:.1%}", flush=True)
            if ratio < best_ratio:
                best_ratio, best_img = ratio, img
            if ratio <= acceptable_ratio:
                return _encode_webp(img)
        except Exception as e:  # noqa: BLE001
            last_err = e
            print(f"  (attempt {attempt} failed: {e}; retrying)", flush=True)
            time.sleep(3)
    if last_err is not None and best_img is None:
        raise RuntimeError(f"Thumbnail generation failed after {max_attempts} attempts: {last_err}")
    raise RuntimeError(
        f"Thumbnail off-brand ratio {best_ratio:.1%} exceeded acceptable {acceptable_ratio:.0%} "
        f"across {max_attempts} attempts. Refusing to publish contaminated thumbnail."
    )


CARD_TEMPLATE = """
                <article class="blog-card">
                    <div class="blog-card__img">
                        <img src="assets/images/blog/blog-{slug}.webp" alt="{title_attr}" loading="lazy" width="400" height="240">
                    </div>
                    <div class="blog-card__body">
                        <div class="blog-meta">
                            <span class="blog-tag">{tag}</span>
                            <time class="blog-date" datetime="{date}">{date_human}</time>
                        </div>
                        <h3 class="blog-title">{title_text}</h3>
                        <a href="blog/{slug}.html" class="blog-link">Read Article
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="7" y1="17" x2="17" y2="7"></line><polyline points="7 7 17 7 17 17"></polyline></svg>
                        </a>
                    </div>
                </article>
"""


def patch_blog_index(topic: dict) -> str:
    text = BLOG_INDEX.read_text(encoding="utf-8")
    marker = '<!-- All Posts -->\n            <div class="blog-grid">\n'
    if marker not in text:
        raise RuntimeError("blog.html grid marker not found")
    card = CARD_TEMPLATE.format(
        slug=topic["slug"],
        title_text=html.escape(topic["title"]),
        title_attr=html.escape(topic["title"], quote=True),
        tag=html.escape(topic["tag"]),
        date=TODAY,
        date_human=DATE_HUMAN,
    )
    return text.replace(marker, marker + card, 1)


def patch_sitemap(topic: dict) -> str:
    text = SITEMAP.read_text(encoding="utf-8")
    entry = (
        "    <url>\n"
        f"        <loc>https://sarvaya.in/blog/{topic['slug']}.html</loc>\n"
        f"        <lastmod>{TODAY}</lastmod>\n"
        "        <changefreq>monthly</changefreq>\n"
        "        <priority>0.6</priority>\n"
        "    </url>\n"
    )
    return text.replace("</urlset>", entry + "</urlset>")


def patch_llms(topic: dict) -> str:
    text = LLMS.read_text(encoding="utf-8")
    lines = text.split("\n")
    last_idx = -1
    for i, ln in enumerate(lines):
        if ln.startswith("- [") and "/blog/" in ln and ".html)" in ln:
            last_idx = i
    if last_idx == -1:
        raise RuntimeError("No blog article lines found in llms.txt")
    new_line = f"- [{topic['title']}](https://sarvaya.in/blog/{topic['slug']}.html)"
    lines.insert(last_idx + 1, new_line)
    return "\n".join(lines)


def main() -> None:
    for var in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY"):
        if not os.environ.get(var):
            sys.exit(f"Missing required env var: {var}")

    category = pick_category()
    print(f"[1/5] Researching trending topic in category: {category[0]}", flush=True)
    topic = research_topic(attempt=1, category=category)
    print(f"  -> slug: {topic['slug']}", flush=True)
    print(f"  -> title: {topic['title']}", flush=True)

    if topic["slug"] in existing_slugs():
        print("  (slug collision, retrying research)", flush=True)
        topic = research_topic(attempt=2, category=category)
        print(f"  -> slug: {topic['slug']}", flush=True)
        print(f"  -> title: {topic['title']}", flush=True)
        if topic["slug"] in existing_slugs():
            sys.exit(f"Slug '{topic['slug']}' still collides after retry - aborting")

    print("[2/5] Generating article HTML...", flush=True)
    article_html = generate_article_html(topic)
    print(f"  -> {len(article_html):,} chars", flush=True)

    expected_img = f"blog-{topic['slug']}.webp"
    if expected_img not in article_html:
        sys.exit(f"Generated article does not reference {expected_img} — aborting")

    # Verify every other image reference points to a file that actually exists
    referenced = set(re.findall(r"blog-[a-z0-9-]+\.webp", article_html))
    referenced.discard(expected_img)
    existing_images = {p.name for p in IMAGES_DIR.glob("blog-*.webp")}
    missing = referenced - existing_images
    if missing:
        sys.exit(f"Article references non-existent images: {sorted(missing)} - aborting")

    # Enforce writing rules. Em/en dashes are auto-normalized upstream;
    # here we only hard-fail on banned AI-slop vocabulary.
    body_match = re.search(
        r'<article class="blog-body">(.*?)</article>', article_html, re.DOTALL
    )
    body_text = body_match.group(1) if body_match else article_html
    banned = [
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
    ]
    lower = body_text.lower()
    hits = [w for w in banned if w in lower]
    if hits:
        sys.exit(f"Article body contains banned phrases {hits} - aborting (see writing_style.md)")

    print("[3/5] Generating thumbnail...", flush=True)
    webp_bytes = generate_thumbnail(topic)
    print(f"  -> {len(webp_bytes):,} bytes WebP", flush=True)

    print("[4/5] Computing patched files (in memory)...", flush=True)
    new_blog_index = patch_blog_index(topic)
    new_sitemap = patch_sitemap(topic)
    new_llms = patch_llms(topic)
    topics = load_topics()
    topics.append({
        "slug": topic["slug"],
        "title": topic["title"],
        "date": TODAY,
        "tag": topic.get("tag", ""),
    })

    print("[5/5] Writing all files to disk...", flush=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    (BLOG_DIR / f"{topic['slug']}.html").write_text(article_html, encoding="utf-8")
    (IMAGES_DIR / f"blog-{topic['slug']}.webp").write_bytes(webp_bytes)
    BLOG_INDEX.write_text(new_blog_index, encoding="utf-8")
    SITEMAP.write_text(new_sitemap, encoding="utf-8")
    LLMS.write_text(new_llms, encoding="utf-8")
    TOPICS_LOG.write_text(json.dumps(topics, indent=2) + "\n", encoding="utf-8")

    print(f"Done: blog/{topic['slug']}.html", flush=True)

    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as f:
            f.write(f"slug={topic['slug']}\n")
            f.write(f"title={topic['title']}\n")


if __name__ == "__main__":
    main()
