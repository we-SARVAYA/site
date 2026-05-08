"""Backfill FAQ HTML+schema and HowTo schema across pre-mandate blog posts.

Reads each post in blog/, skips posts that already have <section class="blog-faq",
asks Gemini for 3-5 post-specific FAQs, injects FAQ HTML before
<section class="blog-related">, and injects FAQPage JSON-LD before </head>.

For HOWTO_TARGETS, additionally injects a HowTo JSON-LD block (no visible HTML
change - the steps are already in the article body).

Usage:
    python scripts/backfill_faq_howto.py [--dry-run] [--only post-slug]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from html import unescape
from pathlib import Path

from google import genai
from google.genai import types as gtypes

ROOT = Path(__file__).resolve().parents[1]
BLOG_DIR = ROOT / "blog"
ENV_FILE = ROOT / ".env"

# Posts that should also receive a HowTo JSON-LD block.
HOWTO_TARGETS = {
    # Round 1 - already shipped
    "llms-txt-explained-implementation-guide-2026",
    "remix-3-drops-react-preact-migration-guide",
    "ios26-sdk-deadline-react-native-flutter-migration",
    "schema-markup-ai-overviews-citation-priority",
    "google-ai-overviews-second-referral-geo-playbook",
    "claude-code-hooks-developer-automation-patterns",
    "ai-automation-small-business",
    "white-label-growth-hack",
    # Round 2 - additional genuine step-style posts
    "ios26-liquid-glass-wcag-contrast-ux-fix",          # contrast fix steps
    "figma-weave-ai-workflows-creative-production-2026", # workflow setup
    "google-workspace-studio-no-code-ai-agents",        # building agents
    "ietf-aipref-ai-crawler-content-preferences-standard", # implementation
    "zapier-mcp-ai-agents-9000-apps-automation",        # connecting Zapier MCP
    "vercel-workflows-ga-durable-nextjs-architecture",  # adopting Workflows
    "ai-citations-vs-google-rankings-geo-strategy",     # GEO strategy execution
    "seo-in-2026",                                      # SEO playbook
    "claude-agent-sdk-python-launch-2026",              # SDK getting started
    "productized-outcome-packages-white-label",         # productizing process
    "agency-model-broken-productized-pivot-2026",       # pivot process
    "brand-storytelling-substack-reddit-2026",          # storytelling execution
    # Round 3 - newly-published posts from auto-queue
    "inp-core-web-vitals-react-debugging-guide",        # INP debugging steps
    "pillar-cluster-content-architecture-modern-seo",   # content architecture
    "react-server-components-error-boundaries-workarounds",  # error boundary workaround steps
}

GEMINI_TEXT_MODEL = "gemini-2.5-flash"


# --------------------------------------------------------------------------- env

def load_env() -> None:
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


# ------------------------------------------------------------------------- parse

ARTICLE_RE = re.compile(r'<article[^>]*class="[^"]*blog-article[^"]*"[^>]*>(.*?)</article>', re.S)
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S)
HEADLINE_RE = re.compile(r'"headline"\s*:\s*"([^"]+)"')
BLOG_RELATED_RE = re.compile(r'\n\s*<!--\s*Related Posts\s*-->\s*\n\s*<section class="blog-related"', re.S)
BLOG_RELATED_FALLBACK_RE = re.compile(r'<section class="blog-related"', re.S)
GA_SCRIPT_RE = re.compile(r'\n\s*<script>window\.GA_MEASUREMENT_ID')
HEAD_CLOSE_RE = re.compile(r"</head>")


def strip_tags(html: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", html)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_article_text(html: str) -> str:
    m = ARTICLE_RE.search(html)
    body = m.group(1) if m else html
    return strip_tags(body)


def extract_title(html: str) -> str:
    m = HEADLINE_RE.search(html)
    if m:
        return m.group(1)
    m = H1_RE.search(html)
    if m:
        return strip_tags(m.group(1))
    return ""


def extract_h2s(html: str) -> list[str]:
    return [strip_tags(x) for x in re.findall(r"<h2[^>]*>(.*?)</h2>", html, re.S)]


# ---------------------------------------------------------------------- gemini

_client: genai.Client | None = None


def _genai() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


def _gen_json(prompt: str, max_attempts: int = 3) -> dict:
    last = None
    for attempt in range(1, max_attempts + 1):
        try:
            resp = _genai().models.generate_content(
                model=GEMINI_TEXT_MODEL,
                contents=prompt,
                config=gtypes.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.4,
                ),
            )
            text = (resp.text or "").strip()
            return json.loads(text)
        except Exception as e:  # noqa: BLE001
            last = e
            if attempt < max_attempts:
                time.sleep(3)
    raise RuntimeError(f"Gemini failed after {max_attempts} attempts: {last}")


FAQ_PROMPT = """You write FAQs for a digital agency blog (sarvaya.in). Generate 4 high-quality FAQs for the blog post below.

Hard rules (from the site spec):
- Each question MUST be a real long-tail query a user would type into Google or ask an AI engine (People Also Ask style).
- Each question MUST be different from any H2 in the article body listed below.
- 40-100 words per answer; first sentence answers directly.
- Concrete specifics (numbers, dates, named tools, percentages where possible).
- No banned vocabulary: avoid "delve", "leverage", "robust", "seamless", "comprehensive", "ever-evolving", "navigating the landscape", em-dashes (use hyphens), and "moreover/furthermore".
- One answer should naturally include exactly one internal link to a relevant SARVAYA service. Pick from these and embed as <a href="URL">descriptive anchor text</a> inside the answer paragraph:
  /services/web-development , /services/ai-automation , /services/seo-geo , /whitelabel , /24hrs , /contact
- Plain text in answers except for the single optional <a> link and inline <strong>/<em> if needed. No other HTML.

Post title: {title}

Existing H2s in the article (do NOT duplicate these as questions):
{h2s}

Article body (truncated):
{body}

Return STRICT JSON in this shape, no markdown fences:
{{
  "faqs": [
    {{"q": "Question 1?", "a": "Answer 1."}},
    {{"q": "Question 2?", "a": "Answer 2."}},
    {{"q": "Question 3?", "a": "Answer 3."}},
    {{"q": "Question 4?", "a": "Answer 4."}}
  ]
}}
"""

HOWTO_PROMPT = """Extract a HowTo schema from the blog post below. The post should already describe a step-by-step process; identify 4-7 sequential, actionable steps from the body.

Post title: {title}

Article body (truncated):
{body}

Return STRICT JSON, no markdown fences:
{{
  "name": "How to <verb phrase derived from post topic>",
  "description": "1-2 sentence summary of what the reader will accomplish.",
  "totalTime": "PT30M or PT2H or similar ISO-8601 duration",
  "steps": [
    {{"name": "Short step title", "text": "1-3 sentence imperative explanation."}},
    ...
  ]
}}

Rules:
- Steps must be in execution order.
- Step text must be imperative ("Run X", "Configure Y") and 20-60 words.
- No banned vocabulary (delve, leverage, robust, seamless, comprehensive). No em-dashes; use hyphens.
"""


def gen_faqs(title: str, body: str, h2s: list[str]) -> list[dict]:
    body_trimmed = body[:8000]
    prompt = FAQ_PROMPT.format(
        title=title,
        h2s="\n".join(f"- {h}" for h in h2s) or "(none)",
        body=body_trimmed,
    )
    data = _gen_json(prompt)
    faqs = data.get("faqs") or []
    if not (3 <= len(faqs) <= 5):
        raise RuntimeError(f"FAQ count out of range: {len(faqs)}")
    for f in faqs:
        if "q" not in f or "a" not in f:
            raise RuntimeError(f"Bad FAQ shape: {f}")
    return faqs


def gen_howto(title: str, body: str) -> dict:
    prompt = HOWTO_PROMPT.format(title=title, body=body[:8000])
    data = _gen_json(prompt)
    if not data.get("steps") or len(data["steps"]) < 3:
        raise RuntimeError(f"HowTo step count too low: {len(data.get('steps', []))}")
    return data


# -------------------------------------------------------------------- builders

def html_escape_text(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_faq_section(faqs: list[dict]) -> str:
    items = []
    for f in faqs:
        q = f["q"].strip()
        a_html = f["a"].strip()
        items.append(
            "                <details class=\"blog-faq__item\">\n"
            f"                    <summary class=\"blog-faq__q\"><span class=\"blog-faq__q-text\">{q}</span></summary>\n"
            "                    <div class=\"blog-faq__a\">\n"
            f"                        <p>{a_html}</p>\n"
            "                    </div>\n"
            "                </details>"
        )
    items_html = "\n".join(items)
    return (
        "    <!-- FAQ -->\n"
        "    <section class=\"blog-faq\" aria-labelledby=\"blog-faq-heading\">\n"
        "        <div class=\"container\">\n"
        "            <div class=\"blog-faq__label\">Common Questions</div>\n"
        "            <h2 id=\"blog-faq-heading\" class=\"blog-faq__title\">Frequently Asked Questions</h2>\n"
        "            <div class=\"blog-faq__list\">\n"
        f"{items_html}\n"
        "            </div>\n"
        "        </div>\n"
        "    </section>\n\n"
    )


def render_faq_schema(faqs: list[dict]) -> str:
    plain_faqs = []
    for f in faqs:
        # answer text in JSON should be plain text (no HTML tags)
        a_plain = strip_tags(f["a"])
        plain_faqs.append({
            "@type": "Question",
            "name": f["q"].strip(),
            "acceptedAnswer": {"@type": "Answer", "text": a_plain},
        })
    block = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": plain_faqs,
    }
    body = json.dumps(block, indent=4, ensure_ascii=False)
    body = "\n".join("    " + line for line in body.splitlines())
    return f"    <script type=\"application/ld+json\">\n{body}\n    </script>\n"


def render_howto_schema(howto: dict) -> str:
    steps = []
    for i, s in enumerate(howto["steps"], 1):
        steps.append({
            "@type": "HowToStep",
            "position": i,
            "name": s["name"],
            "text": s["text"],
        })
    block = {
        "@context": "https://schema.org",
        "@type": "HowTo",
        "name": howto["name"],
        "description": howto.get("description", ""),
        "step": steps,
    }
    if howto.get("totalTime"):
        block["totalTime"] = howto["totalTime"]
    body = json.dumps(block, indent=4, ensure_ascii=False)
    body = "\n".join("    " + line for line in body.splitlines())
    return f"    <script type=\"application/ld+json\">\n{body}\n    </script>\n"


# --------------------------------------------------------------------- inject

def inject(html: str, faq_html: str, faq_schema: str, howto_schema: str | None) -> str:
    # Insert FAQ HTML before "Related Posts" comment + section if present, else
    # before the bare <section class="blog-related">.
    new_html = html
    if BLOG_RELATED_RE.search(new_html):
        new_html = BLOG_RELATED_RE.sub(
            "\n\n" + faq_html + "    <!-- Related Posts -->\n    <section class=\"blog-related\"",
            new_html,
            count=1,
        )
    else:
        new_html = BLOG_RELATED_FALLBACK_RE.sub(
            faq_html + "    <section class=\"blog-related\"",
            new_html,
            count=1,
        )

    # Insert schema(s) before the GA measurement script (which sits just before </head>).
    extras = faq_schema + (howto_schema or "")
    if GA_SCRIPT_RE.search(new_html):
        new_html = GA_SCRIPT_RE.sub("\n" + extras + "    <script>window.GA_MEASUREMENT_ID", new_html, count=1)
    else:
        new_html = HEAD_CLOSE_RE.sub(extras + "</head>", new_html, count=1)
    return new_html


# ----------------------------------------------------------------------- main

def process(path: Path, dry_run: bool, howto_add_only: bool = False) -> str:
    html = path.read_text(encoding="utf-8")

    # Mode: only inject HowTo schema (skip FAQ generation entirely).
    if howto_add_only:
        if '"@type": "HowTo"' in html:
            return "skip-already-has-howto"
        if path.stem not in HOWTO_TARGETS:
            return "skip-not-howto-target"
        title = extract_title(html)
        body = extract_article_text(html)
        if len(body) < 500:
            return "skip-body-too-short"
        print(f"  generating HowTo for {path.stem} ...", flush=True)
        howto = gen_howto(title, body)
        howto_schema = render_howto_schema(howto)
        if GA_SCRIPT_RE.search(html):
            new_html = GA_SCRIPT_RE.sub("\n" + howto_schema + "    <script>window.GA_MEASUREMENT_ID", html, count=1)
        else:
            new_html = HEAD_CLOSE_RE.sub(howto_schema + "</head>", html, count=1)
        if dry_run:
            return "dry-run-howto-added"
        path.write_text(new_html, encoding="utf-8")
        return "updated-howto-added"

    if 'class="blog-faq"' in html or '"@type": "FAQPage"' in html:
        return "skip-already-has-faq"
    title = extract_title(html)
    if not title:
        return "skip-no-title"
    body = extract_article_text(html)
    if len(body) < 500:
        return "skip-body-too-short"
    h2s = extract_h2s(html)

    print(f"  generating FAQs for {path.stem} ...", flush=True)
    faqs = gen_faqs(title, body, h2s)
    faq_html = render_faq_section(faqs)
    faq_schema = render_faq_schema(faqs)

    howto_schema = None
    if path.stem in HOWTO_TARGETS:
        print(f"  generating HowTo for {path.stem} ...", flush=True)
        howto = gen_howto(title, body)
        howto_schema = render_howto_schema(howto)

    new_html = inject(html, faq_html, faq_schema, howto_schema)

    if dry_run:
        return f"dry-run-faqs={len(faqs)}-howto={'yes' if howto_schema else 'no'}"
    path.write_text(new_html, encoding="utf-8")
    return f"updated-faqs={len(faqs)}-howto={'yes' if howto_schema else 'no'}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", default=None, help="single post slug to process")
    ap.add_argument("--howto-only", action="store_true", help="only run on HOWTO_TARGETS posts")
    ap.add_argument("--howto-add", action="store_true", help="add HowTo schema to HOWTO_TARGETS posts that already have FAQ but no HowTo")
    args = ap.parse_args()

    load_env()
    if "GEMINI_API_KEY" not in os.environ:
        print("ERROR: GEMINI_API_KEY missing", file=sys.stderr)
        return 1

    posts = sorted(BLOG_DIR.glob("*.html"))
    if args.only:
        posts = [p for p in posts if p.stem == args.only]
    if args.howto_only:
        posts = [p for p in posts if p.stem in HOWTO_TARGETS]

    print(f"Processing {len(posts)} post(s) (dry_run={args.dry_run})")
    results: dict[str, str] = {}
    for p in posts:
        try:
            r = process(p, args.dry_run, howto_add_only=args.howto_add)
        except Exception as e:  # noqa: BLE001
            r = f"ERROR: {e}"
        results[p.stem] = r
        print(f"  {p.stem}: {r}", flush=True)

    print("\nSummary:")
    counts: dict[str, int] = {}
    for r in results.values():
        key = r.split("-")[0] if not r.startswith("ERROR") else "error"
        counts[key] = counts.get(key, 0) + 1
    for k, v in counts.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
