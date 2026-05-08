#!/usr/bin/env python3
"""Auto-publish a blog post for sarvaya.in.

Pipeline:
  1. Research a trending topic via OpenAI Responses API + web_search tool.
  2. Generate the full blog HTML via OpenAI Chat Completions, copying
     structure from an existing post.
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
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from openai import OpenAI
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
BLOG_DIR = ROOT / "blog"
IMAGES_DIR = ROOT / "assets" / "images" / "blog"
BLOG_INDEX = ROOT / "blog.html"
HOME_INDEX = ROOT / "index.html"
SITEMAP = ROOT / "sitemap.xml"
LLMS = ROOT / "llms.txt"
TOPICS_LOG = Path(__file__).resolve().parent / "topics_log.json"
STYLE_FILE = Path(__file__).resolve().parent / "writing_style.md"
SPEC_FILE = Path(__file__).resolve().parent / "blog_post_spec.md"
REFERENCE_POST = BLOG_DIR / "seo-in-2026.html"

TODAY = datetime.now(timezone.utc).date().isoformat()
DATE_HUMAN = datetime.strptime(TODAY, "%Y-%m-%d").strftime("%d %B %Y")

GEMINI_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")

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


_openai_client: OpenAI | None = None


def _client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI()
    return _openai_client


def run_llm(prompt: str, allow_web: bool = False, timeout: int = 900, max_attempts: int = 2) -> str:
    """Call OpenAI. With allow_web=True uses the Responses API + web_search tool;
    otherwise plain Chat Completions. Returns the model's text output."""
    last_err: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            if allow_web:
                resp = _client().responses.create(
                    model=OPENAI_MODEL,
                    input=prompt,
                    tools=[{"type": "web_search"}],
                    timeout=timeout,
                )
                text = (resp.output_text or "").strip()
            else:
                resp = _client().chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    max_completion_tokens=16000,
                    timeout=timeout,
                )
                text = (resp.choices[0].message.content or "").strip()
            if not text:
                raise RuntimeError("OpenAI returned empty output")
            return text
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt < max_attempts:
                print(f"  OpenAI call failed (attempt {attempt}/{max_attempts}): {e}; retrying in 5s", flush=True)
                time.sleep(5)
    raise RuntimeError(f"OpenAI failed after {max_attempts} attempts: {last_err}")


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

Use the web_search tool to find ONE trending, newsworthy story from the past 14 days within that category. Prefer specific, actionable angles (e.g. "How the new Core Web Vitals INP threshold changes React app design") over generic evergreens ("Why UX matters"). The topic must be concrete enough that an expert could write 1200+ words with named tools, numbers, and specific techniques.

MUST NOT duplicate any of these existing slugs:
{exclusions}{tries_hint}

Output ONLY minified JSON (no markdown fences, no preamble). Schema:
{{"slug":"kebab-case-slug-max-50-chars","title":"5-14 word title","tag":"{cat_tag}","excerpt":"1-2 sentences under 160 chars","keywords":["kw1","kw2","kw3","kw4","kw5","kw6"],"thumbnail_prompt":"detailed abstract visual description for a 1200x675 hero image - no text, no logos, no named brand references"}}"""
    raw = run_llm(prompt, allow_web=True)
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


def generate_article_html(topic: dict, extra_hint: str = "") -> str:
    reference = REFERENCE_POST.read_text(encoding="utf-8")
    style_rules = STYLE_FILE.read_text(encoding="utf-8")
    master_spec = SPEC_FILE.read_text(encoding="utf-8") if SPEC_FILE.exists() else ""
    hint_block = f"\n\n{extra_hint.strip()}\n" if extra_hint.strip() else ""
    banlist_literal = ", ".join(f'"{w}"' for w in BANNED_PHRASES)
    banned_reminder = (
        "BEFORE YOU WRITE A SINGLE WORD: the article body is run through an automated reject filter. "
        "ANY of the following words/phrases (case-insensitive substring match, including their tenses, "
        "plurals, and -ing/-ed forms) appearing ANYWHERE in the <article class=\"blog-body\"> block "
        f"will cause the post to be discarded:\n  {banlist_literal}\n"
        "This is a hard automated check — not a stylistic preference. If you reach for one of these "
        "mid-sentence, STOP and rewrite the sentence with a plain, specific alternative. Prefer concrete "
        "verbs and named tools over abstract corporate vocabulary. Do not paraphrase the banned terms "
        "with close synonyms either (e.g. 'frictionless' instead of 'seamless' is still slop)."
    )
    prompt = f"""Produce a complete standalone HTML blog post for sarvaya.in.

{banned_reminder}{hint_block}

<<<MASTER_SPEC (every rule below is mandatory; violation = post rejected)
{master_spec}
MASTER_SPEC

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
- canonical: https://sarvaya.in/blog/{topic['slug']}
- image path in HTML: ../assets/images/blog/blog-{topic['slug']}.webp
- og:image full URL: https://sarvaya.in/assets/images/blog/blog-{topic['slug']}.webp

CONTENT REQUIREMENTS
- Write a 1200-1600 word expert article body
- Mirror the reference's heading hierarchy (h2/h3), TL;DR aside, blockquote,
  unordered lists, ordered lists, and <strong> emphasis patterns
- Confident first-person-plural voice, no filler, no "in this article we will"
- Include concrete specifics, numbers, and named tools/platforms
- Update every meta tag, og:, twitter:, canonical, JSON-LD BlogPosting,
  JSON-LD BreadcrumbList, article:published_time, article:modified_time,
  title tag, meta description, meta keywords
- **MANDATORY FAQ SECTION** between </div> closing .blog-layout and the
  <section class="blog-related"> block. Copy the EXACT structure from the
  reference post's <section class="blog-faq"> element. Requirements:
    * 3-5 questions, 5 is ideal
    * Questions are real long-tail queries someone would type, NOT paraphrased
      versions of the article H2s
    * 40-100 word answers, first sentence directly answers the question
    * At least one answer contains an internal link to a service page
      (/services/web-development, /services/ai-automation, /services/seo-geo,
      /whitelabel, /24hrs) or a related blog post
    * Use semantic <details>/<summary> with classes blog-faq__item,
      blog-faq__q, blog-faq__a. The question text MUST be wrapped in
      <span class="blog-faq__q-text"> inside the summary tag (so the
      flex layout handles long questions correctly with the prefix
      number and suffix icon).
- **MANDATORY FAQPage JSON-LD schema** in <head> immediately after the
  BreadcrumbList script. Questions and answers must MATCH the visible FAQ
  section verbatim (plain text, no HTML in schema answers). See reference
  post for the exact structure.
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
    raw = run_llm(prompt, allow_web=False, timeout=900)
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
    """Parse the existing featured block so it can be rebuilt as a card."""
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
    """Insert card before the first existing grid card whose datetime is older."""
    marker = '<!-- All Posts -->\n            <div class="blog-grid">\n'
    if marker not in text:
        raise RuntimeError("blog.html grid marker not found")
    grid_start = text.find(marker) + len(marker)
    card_pattern = re.compile(r'<article class="blog-card">.*?</article>', re.DOTALL)
    for m in card_pattern.finditer(text, pos=grid_start):
        dt_m = re.search(r'<time class="blog-date" datetime="([^"]+)"', m.group(0))
        # Use <= so a demoted card with the same date as existing cards lands
        # at the top of its date group (it's the most recently demoted).
        if dt_m and dt_m.group(1) <= card_datetime:
            # Insert directly before this older card. The card template carries
            # its own leading newline + indentation; trim whitespace already at
            # this position to avoid stacking blank lines.
            insert_at = m.start()
            # back up to start of the line so we drop the existing 16-space indent
            line_start = text.rfind("\n", 0, insert_at) + 1
            return text[:line_start] + card_html.lstrip("\n") + "\n" + text[line_start:]
    # All existing cards are newer (or grid empty) -> insert at top of grid.
    return text.replace(marker, marker + card_html, 1)


def _latest_posts_from_blog_index(blog_index_html: str, n: int = 3) -> list[dict]:
    """Extract the n most recent posts from blog.html (featured + top grid cards)."""
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
    """Replace the 3 hardcoded cards in index.html "Our Blogs" with the latest 3."""
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
    # CARD_TEMPLATE has a leading newline; trim it so the first card sits flush
    # with the grid's opening blank line. Trailing newline kept as separator.
    return text[:m.start(2)] + cards_html.lstrip("\n").rstrip("\n") + text[m.end(2):]


def patch_blog_index(topic: dict) -> str:
    """Promote the new topic into the featured slot, demote the previous featured to a card."""
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
        date=TODAY,
        date_human=DATE_HUMAN,
    )
    text = text[:featured_match.start()] + new_featured + text[featured_match.end():]

    # Demote previous featured -> card. Skip if the slug is already represented
    # as a card (defensive, in case of an earlier botched rotation).
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


def patch_sitemap(topic: dict) -> str:
    text = SITEMAP.read_text(encoding="utf-8")
    entry = (
        "    <url>\n"
        f"        <loc>https://sarvaya.in/blog/{topic['slug']}</loc>\n"
        f"        <lastmod>{TODAY}</lastmod>\n"
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
    # Fallback: no existing blog line found — append at end instead of failing
    if text and not text.endswith("\n"):
        text += "\n"
    return text + new_line + "\n"


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
]


def _research_topic_with_retry(category: tuple, max_attempts: int = 3) -> dict:
    """Research a topic and retry on slug collisions or malformed LLM output."""
    last_err: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            topic = research_topic(attempt=attempt, category=category)
        except (ValueError, RuntimeError, json.JSONDecodeError) as e:
            last_err = e
            print(f"  research attempt {attempt}/{max_attempts} failed: {e}; retrying", flush=True)
            time.sleep(2)
            continue
        if topic["slug"] in existing_slugs():
            last_err = ValueError(f"slug collision: {topic['slug']}")
            print(f"  research attempt {attempt}/{max_attempts}: slug collision, retrying", flush=True)
            continue
        return topic
    raise RuntimeError(f"Topic research failed after {max_attempts} attempts: {last_err}")


def _generate_validated_article_with_retry(topic: dict, max_attempts: int = 3) -> str:
    """Generate the article HTML, validate it, and retry with feedback on failure.

    Retryable failures: malformed output (no DOCTYPE block), missing required
    image reference, references to nonexistent images, banned phrases.
    On each retry the prompt receives a hint listing prior offenses so Claude
    can avoid repeating them.
    """
    expected_img = f"blog-{topic['slug']}.webp"
    existing_images = {p.name for p in IMAGES_DIR.glob("blog-*.webp")}

    banned_history: list[str] = []
    structural_history: list[str] = []
    last_err: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        hint_parts: list[str] = []
        if banned_history:
            uniq = sorted(set(banned_history))
            hint_parts.append(
                "PRIOR ATTEMPT FAILED — your output contained these banned words/phrases: "
                f"{uniq}. Do NOT use any of them, their tenses, plurals, or close synonyms in any part of the article body."
            )
        if structural_history:
            hint_parts.append(
                "PRIOR ATTEMPT FAILED — output was malformed. Your entire response MUST start with "
                "<!DOCTYPE html> and end with </html>. No markdown fences, no narration, no preamble. "
                f"All blog-*.webp filenames must come from the mandatory related-post mapping AND must reference {expected_img} for the cover."
            )
        extra_hint = "\n\n".join(hint_parts)

        try:
            article_html = generate_article_html(topic, extra_hint=extra_hint)
        except ValueError as e:
            structural_history.append(f"malformed: {str(e)[:120]}")
            last_err = e
            print(f"  generation attempt {attempt}/{max_attempts}: malformed output, retrying", flush=True)
            continue
        except RuntimeError as e:
            last_err = e
            print(f"  generation attempt {attempt}/{max_attempts}: LLM error: {e}; retrying", flush=True)
            time.sleep(3)
            continue

        if expected_img not in article_html:
            structural_history.append(f"missing required cover image {expected_img}")
            last_err = RuntimeError(f"article missing required image {expected_img}")
            print(f"  generation attempt {attempt}/{max_attempts}: cover image not referenced, retrying", flush=True)
            continue

        referenced = set(re.findall(r"blog-[a-z0-9-]+\.webp", article_html))
        referenced.discard(expected_img)
        invented = referenced - existing_images
        if invented:
            structural_history.append(f"invented images {sorted(invented)}")
            last_err = RuntimeError(f"article references nonexistent images {sorted(invented)}")
            print(f"  generation attempt {attempt}/{max_attempts}: invented images {sorted(invented)}, retrying", flush=True)
            continue

        body_match = re.search(
            r'<article class="blog-body">(.*?)</article>', article_html, re.DOTALL
        )
        body_text = body_match.group(1) if body_match else article_html
        lower = body_text.lower()
        hits = [w for w in BANNED_PHRASES if w in lower]
        if hits:
            banned_history.extend(hits)
            last_err = RuntimeError(f"banned phrases {hits}")
            print(f"  generation attempt {attempt}/{max_attempts}: banned phrases {hits}, retrying", flush=True)
            continue

        # FAQ structural validation (see scripts/faq_spec.md)
        faq_section_present = '<section class="blog-faq"' in article_html
        faq_schema_present = '"@type": "FAQPage"' in article_html or '"@type":"FAQPage"' in article_html
        faq_item_count = len(re.findall(r'<details class="blog-faq__item"', article_html))
        faq_problems = []
        if not faq_section_present:
            faq_problems.append("missing <section class=\"blog-faq\">")
        if not faq_schema_present:
            faq_problems.append("missing FAQPage JSON-LD schema")
        if faq_item_count < 3:
            faq_problems.append(f"only {faq_item_count} FAQ items (need 3-5)")
        elif faq_item_count > 5:
            faq_problems.append(f"{faq_item_count} FAQ items (max 5)")
        if faq_problems:
            last_err = RuntimeError(f"FAQ validation failed: {faq_problems}")
            print(f"  generation attempt {attempt}/{max_attempts}: FAQ {faq_problems}, retrying", flush=True)
            continue

        # Schema + linking validation (see scripts/blog_post_spec.md)
        spec_problems = []
        if '"@type": "BlogPosting"' not in article_html:
            spec_problems.append("missing BlogPosting JSON-LD")
        if '"@type": "BreadcrumbList"' not in article_html:
            spec_problems.append("missing BreadcrumbList JSON-LD")

        # In-body links: count anchors inside <article ...> that point to SARVAYA pages.
        article_match = re.search(r'<article[^>]*class="[^"]*blog-article[^"]*"[^>]*>([\s\S]*?)</article>', article_html)
        article_inner = article_match.group(1) if article_match else ""
        internal_link_pattern = r'<a\s+[^>]*href="(?:/(?:services/|24hrs|whitelabel|portfolio|contact|blog/)|https://sarvaya\.in/|https://freetools\.sarvaya\.in)[^"]*"'
        internal_count = len(re.findall(internal_link_pattern, article_inner))
        if internal_count < 3:
            spec_problems.append(f"only {internal_count} in-body internal links (need >= 3)")

        # Outbound authority links: count anchors with target=_blank and external href in body.
        outbound_pattern = r'<a\s+[^>]*href="https?://(?!sarvaya\.in|freetools\.sarvaya\.in|wa\.me|twitter\.com|linkedin\.com)[^"]+"[^>]*target="_blank"'
        outbound_count = len(re.findall(outbound_pattern, article_inner))
        if outbound_count < 2:
            spec_problems.append(f"only {outbound_count} outbound authority links (need >= 2)")

        if spec_problems:
            last_err = RuntimeError(f"Spec validation failed: {spec_problems}")
            print(f"  generation attempt {attempt}/{max_attempts}: spec {spec_problems}, retrying", flush=True)
            continue

        return article_html

    raise RuntimeError(f"Article generation failed after {max_attempts} attempts. Last error: {last_err}")


def main() -> None:
    for var in ("OPENAI_API_KEY", "GEMINI_API_KEY"):
        if not os.environ.get(var):
            sys.exit(f"Missing required env var: {var}")

    category = pick_category()
    print(f"[1/5] Researching trending topic in category: {category[0]}", flush=True)
    topic = _research_topic_with_retry(category=category, max_attempts=3)
    print(f"  -> slug: {topic['slug']}", flush=True)
    print(f"  -> title: {topic['title']}", flush=True)

    print("[2/5] Generating article HTML...", flush=True)
    article_html = _generate_validated_article_with_retry(topic, max_attempts=6)
    print(f"  -> {len(article_html):,} chars", flush=True)

    print("[3/5] Generating thumbnail...", flush=True)
    webp_bytes = generate_thumbnail(topic)
    print(f"  -> {len(webp_bytes):,} bytes WebP", flush=True)

    print("[4/5] Computing patched files (in memory)...", flush=True)
    new_blog_index = patch_blog_index(topic)
    new_home_index = patch_home_blog_section(
        _latest_posts_from_blog_index(new_blog_index, n=3)
    )
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
    HOME_INDEX.write_text(new_home_index, encoding="utf-8")
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
