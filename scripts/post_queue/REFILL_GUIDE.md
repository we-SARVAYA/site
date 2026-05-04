# Refill Guide — Blog Post Queue

Read this top-to-bottom before generating posts. The publisher (`scripts/publish_next.py`) runs in CI every 12h and pops the next queued post — your job is to fill the queue with 14 ready-to-ship posts so it has runway for one full week.

## Inputs you must read first
- `scripts/writing_style.md` — voice, banlist, structural rules
- `blog/seo-in-2026.html` — the canonical reference post. Every new post copies its structure exactly: nav, sidebar share buttons, schema blocks, footer scripts, CSS/JS includes — byte-for-byte identical except for the content-specific fields.
- `scripts/topics_log.json` — recent topic history. Don't repeat slugs or near-duplicate angles.
- `scripts/post_queue/manifest.json` — current queue state.

## Step 1: Plan 14 topics

Pick 14 across these 9 categories. Don't load up on one. Aim roughly:
- ~3 GEO/AEO/AI search
- ~2 Claude + AI tooling
- ~2 Traditional SEO
- ~2 Web/App development
- ~1 UI/UX
- ~1 Branding/storytelling
- ~1 AI automation for SMBs
- ~1 Agency/white-label
- ~1 wildcard

Each topic must be:
- **Concrete** — named tools, numbers, real techniques. "How the Core Web Vitals INP threshold breaks React class-component re-renders" beats "Why UX matters."
- **One-week-relevant** — these post over the next 7 days, so news pegs more than a month old will feel stale by Sunday next.
- **Distinct slug** — kebab-case, max 60 chars, not in `topics_log.json` or `blog/`.

Write the topic list out before generating any HTML. Get user signoff if you're unsure.

## Step 2: For each topic, write three things

For slug `your-slug-here`, create:

### a) `scripts/post_queue/posts/your-slug-here.html`
Full standalone HTML, structured exactly like `blog/seo-in-2026.html`. **Critical token rules:**

- The post's *own* publish date appears in TWO spots only — JSON-LD `datePublished` and the byline `<time>` tag. In **both** spots, use the literal token `{{PUBLISH_DATE}}` for the ISO date and `{{PUBLISH_DATE_HUMAN}}` for the display date (e.g., "11 May 2026"). The publisher will substitute the real date on push day.
- `article:modified_time` — also use `{{PUBLISH_DATE}}`.
- **Related posts at the bottom** use real, fixed ISO dates (any of the dates already in `topics_log.json`) — these reference *other* posts that already exist on the site, so they must be literal, not tokenized.
- Cover image: `../assets/images/blog/blog-your-slug-here.webp`
- Canonical: `https://sarvaya.in/blog/your-slug-here`

Body: 1200–1600 words, voice and structure per `writing_style.md`. Run the banlist in your head before writing — every word in `BANNED_PHRASES` (see `scripts/generate_blog.py` for the canonical list) and its tenses/synonyms is forbidden in `<article class="blog-body">`.

### b) `scripts/post_queue/posts/your-slug-here.json`
Optional metadata file (the manifest is the source of truth, but this is handy for diffing). Include the same fields as the manifest entry below.

### c) Add manifest entry — append to `scripts/post_queue/manifest.json` `"posts"` array:

```json
{
  "slug": "your-slug-here",
  "title": "Your 5-14 word title",
  "tag": "GEO|AI|SEO|Development|Design|Branding|Automation|Agency",
  "excerpt": "1-2 sentences under 160 chars for the featured-card description",
  "category": "AEO / GEO / AI search",
  "thumbnail_prompt": "detailed abstract visual description for hero image - no text, no logos, no brand names",
  "queued_at": "2026-05-04T00:00:00Z",
  "published_at": null,
  "status": "queued"
}
```

Order in the array = publish order. The publisher pops from the top.

## Step 3: Generate hero images (one batch)

After all 14 manifest entries + HTML files are written:

```bash
python scripts/queue_helpers.py gen-images
```

Reads the manifest, generates a WebP for any queued post missing one, retries up to 5x per post for off-brand contamination. Requires `GEMINI_API_KEY` in env (use the project `.env`).

If any single post fails, regenerate just that one:
```bash
python scripts/queue_helpers.py gen-image your-slug-here
```

## Step 4: Validate

```bash
python scripts/queue_helpers.py validate
```

Checks every queued post has its HTML, image, the `{{PUBLISH_DATE}}` token, and references its own image. Fails loudly if anything is missing.

## Step 5: Commit and push

Single commit:
```
git add scripts/post_queue/
git commit -m "blog-queue: refill 14 posts for the week of YYYY-MM-DD"
git push
```

The CI publisher will start picking these up on its next 12h tick.

## Rules that have burned us before

- **Don't invent related-post images.** Only reference `blog-*.webp` filenames that already exist in `assets/images/blog/`. Cross-check against the mapping in `scripts/generate_blog.py` (`generate_article_html` function — there's a hardcoded list of 7 related-post candidates).
- **Don't bake today's date into the new post's published-time.** Use the token. If you forget, every post will claim it was published the day you ran refill, not the day it actually went live.
- **One slug, one entry.** Duplicate slugs will trip `validate`.
