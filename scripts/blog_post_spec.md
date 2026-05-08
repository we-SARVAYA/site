# SARVAYA Blog Post Master Spec

This is the single source of truth for every blog post on sarvaya.in. Every new post (manual, queue-published, or pipeline-generated) MUST satisfy every rule below before it ships. The build validator in `scripts/generate_blog.py` enforces the structural rules; the rest are enforced by review.

> **Companion files** (do not duplicate; this file references them):
> - `scripts/writing_style.md` - voice, banned vocabulary, sentence rules
> - `scripts/faq_spec.md` - FAQ block detail rules
> - `scripts/thumbnail_style.md` - hero image style
> - `DESIGN_SYSTEM.md` - site-wide CSS tokens

---

## 1. Required JSON-LD schemas

Every post MUST ship the following JSON-LD blocks in `<head>`, in this exact order:

| # | Schema | Required? | Purpose |
|---|---|---|---|
| 1 | `BlogPosting` | **Always** | Core article identity for Google + AI engines |
| 2 | `BreadcrumbList` | **Always** | Sitelinks + breadcrumb rich result |
| 3 | `FAQPage` | **Always** | AEO/GEO citation, People Also Ask |
| 4 | `HowTo` | **If post is step-style** | Rich result for sequential processes |

### 1.1 BlogPosting - required fields

```jsonc
{
  "@context": "https://schema.org",
  "@type": "BlogPosting",
  "headline": "<= 110 chars, matches H1",
  "description": "<= 160 chars, matches meta description",
  "datePublished": "YYYY-MM-DD",
  "dateModified": "YYYY-MM-DD (>= datePublished)",
  "author": {
    "@type": "Person",
    "name": "SARVAYA Editorial Team",
    "url": "https://sarvaya.in"
  },
  "publisher": {
    "@type": "Organization",
    "name": "SARVAYA",
    "url": "https://sarvaya.in",
    "logo": {"@type": "ImageObject", "url": "https://sarvaya.in/assets/images/logo.png"}
  },
  "mainEntityOfPage": {"@type": "WebPage", "@id": "https://sarvaya.in/blog/<slug>"},
  "image": "https://sarvaya.in/assets/images/blog/blog-<slug>.webp",
  "articleSection": "<one of: AI | SEO | Web | Brand | Agency | UX>"
}
```

### 1.2 BreadcrumbList

Three items: Home > Blog > Post-title. Position 1, 2, 3.

### 1.3 FAQPage

See `scripts/faq_spec.md` (full rules). Summary:
- 3-5 questions, 5 is ideal
- 40-100 word answers
- First sentence answers the question directly
- One answer contains an internal link to a service page or related post
- Schema text must match the visible FAQ verbatim (plain text only, no HTML in `acceptedAnswer.text`)

### 1.4 HowTo - when to include, when to skip

**Include HowTo schema if and only if:**
- The post body contains 3+ sequential, actionable steps a reader can follow.
- Examples that qualify: implementation guides, migration guides, setup walkthroughs, debugging playbooks, fix tutorials.

**Skip HowTo schema if the post is:**
- An opinion piece, comparison, news/policy update, case study, or trend analysis.
- Adding HowTo to non-process content is treated as schema spam by Google and risks rich-result loss across the entire site.

**HowTo block shape:**
```jsonc
{
  "@context": "https://schema.org",
  "@type": "HowTo",
  "name": "How to <verb phrase>",
  "description": "1-2 sentence outcome summary",
  "totalTime": "PT30M",
  "step": [
    {"@type": "HowToStep", "position": 1, "name": "Short title", "text": "20-60 word imperative explanation."}
  ]
}
```
Steps must be in execution order. 4-7 steps is the sweet spot.

### 1.5 Schema validation gates

Before merge / publish, every post MUST pass:
- All JSON-LD blocks parse as valid JSON (no trailing commas, proper escaping).
- `FAQPage.mainEntity[].name` matches the visible `<span class="blog-faq__q-text">` text byte-for-byte.
- `FAQPage.mainEntity[].acceptedAnswer.text` is plain text (no HTML tags) and the meaning matches the visible `<p>` answer.
- `BlogPosting.headline` <= 110 chars; `description` <= 160 chars.
- `dateModified >= datePublished`.

---

## 2. Internal linking (mandatory)

Every post MUST include AT LEAST:

- **3 in-body internal links** to other SARVAYA pages, in the article body (not the nav, sidebar CTA, or related-posts grid).
- **1 internal link inside an FAQ answer** (already required by `faq_spec.md`).
- **3 related-blog cards** in the "More from our blog" section, picked from the mapping in `generate_blog.py`.

Link targets must be drawn from this list (use descriptive anchor text, never "click here"):

| Target | URL | When to link |
|---|---|---|
| Web Development service | `/services/web-development` | Site builds, frontend, performance topics |
| AI Automation service | `/services/ai-automation` | Workflow automation, LLM topics |
| SEO + GEO service | `/services/seo-geo` | SEO, AEO, GEO, schema topics |
| 24hrs delivery page | `/24hrs` | Speed-of-execution claims, MVP topics |
| White Label | `/whitelabel` | Agency/partner topics |
| Portfolio | `/portfolio` | Case-study or proof-needed topics |
| Contact | `/contact` | Call-to-action context |
| Free Tools subdomain | `https://freetools.sarvaya.in` | Tooling/utility topics |
| Related blog post | `/blog/<slug>` | Topical depth, cluster reinforcement |

Anchor-text rules:
- Use the exact phrase a user would search for ("AI automation services", not "our services").
- No more than one link per sentence.
- Never link the same target twice in the same paragraph.

---

## 3. External backlinks / outbound citations (mandatory for AEO/GEO)

AI engines preferentially cite content that itself cites authoritative sources. Every post MUST include:

- **At least 2 outbound links to high-authority sources** (Google, Anthropic, OpenAI, MDN, W3C, IETF, official docs, peer-reviewed research, established trade publications) within the article body.
- Outbound links must use `target="_blank" rel="noopener noreferrer"`.
- Cite the source for every numeric claim, quoted statistic, or named-tool capability.
- Preference order: primary source > vendor docs > major publisher (NYT, WSJ, The Verge) > niche blog. Never cite content farms.
- Anchor text describes the destination ("Google's helpful content guidance", not "this article").

Anti-patterns:
- Linking to a competitor's marketing page as a "source" - cite their docs or a third-party report instead.
- More than 6 outbound links in a single 1500-word post (dilutes link equity).

---

## 4. AEO + GEO content patterns

These are the signals that get content cited by Google AI Overviews, ChatGPT, Perplexity, and Bing Copilot.

### 4.1 Passage-level citability

- Open every H2 section with a **direct-answer paragraph**: 1-2 sentences that fully answer the section heading. AI engines lift these as citations.
- First 100 words of the post must contain the primary keyword and a concrete claim with a number or named entity.
- Use **definition sentences** for any term: `<term> is <definition>` - explicit, no metaphors.

### 4.2 Structural citation hooks

- At least **one bulleted or numbered list** with 3-6 parallel items per major H2.
- At least **one comparison table** OR **one stats callout** per post (tables outperform paragraphs in AI citation pickup).
- One blockquote pulling a strong line - useful as a quotable snippet.
- TL;DR aside at the top (3-5 bullets summarizing the post). This is the highest-cited section for ChatGPT and Perplexity.

### 4.3 Entity density

- Name specific tools, companies, standards, and people. "Google's INP metric" beats "a Core Web Vital".
- Include version numbers and dates wherever possible ("Remix 3.0, released April 2026").
- Prefer proper nouns over generics in the first paragraph.

### 4.4 Freshness signals

- `dateModified` must be updated whenever content materially changes.
- Mention the current year in at least one H2 or the title for evergreen posts that need recurrence.

---

## 5. On-page meta + Open Graph (mandatory)

Every post MUST include in `<head>`:

```html
<title><Post Title> | SARVAYA</title>
<meta name="description" content="<= 160 chars, primary keyword, includes a number">
<meta name="keywords" content="5-7 real search terms, comma-separated">
<meta name="author" content="SARVAYA Editorial Team">
<link rel="canonical" href="https://sarvaya.in/blog/<slug>">

<!-- Open Graph -->
<meta property="og:type" content="article">
<meta property="og:title" content="<Post Title>">
<meta property="og:description" content="<same as meta description>">
<meta property="og:url" content="https://sarvaya.in/blog/<slug>">
<meta property="og:image" content="https://sarvaya.in/assets/images/blog/blog-<slug>.webp">
<meta property="article:published_time" content="<ISO 8601>">
<meta property="article:modified_time" content="<ISO 8601>">

<!-- Twitter -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="<Post Title>">
<meta name="twitter:description" content="<same as meta description>">
<meta name="twitter:image" content="https://sarvaya.in/assets/images/blog/blog-<slug>.webp">
```

Rules:
- `og:image` must be 1200x630 WebP, exists at the path before publish.
- Title tag = `<H1> | SARVAYA` (preserve casing of the H1).
- `description` and `og:description` are byte-identical.

---

## 6. Images + media

- Hero image: 1200x630 WebP at `assets/images/blog/blog-<slug>.webp`.
- Every `<img>` tag MUST have:
  - `alt=` describing the image, naturally including the primary keyword
  - `loading="lazy"` (except the hero image, which is eager)
  - explicit `width=` and `height=` to prevent CLS
- No raster JPG/PNG when WebP is feasible.
- Generate hero via `gen_og_default.py` or `gen_claude_design_thumbnail.py`; follow `scripts/thumbnail_style.md`.

---

## 7. URL + slug rules

- Slug: lowercase, hyphen-separated, 3-7 words, includes primary keyword.
- No years in the slug unless the post is explicitly about that year ("ios26-sdk-deadline-react-native-flutter-migration" is fine; "ai-automation-2026" is not).
- Final URL is `https://sarvaya.in/blog/<slug>` (no trailing slash, no `.html`).

---

## 8. Sitemap + indexation

- Add the post URL to `sitemap.xml` with `<lastmod>` set to publish date and `<priority>0.7</priority>`.
- Verify the URL is reachable, returns 200, and renders fully without JS (server-rendered HTML).
- Submit to GSC via the URL Inspection API after publish (Indexing API also works).
- Confirm the page is referenced from `blog.html` (the index page lists it) within 1 build cycle.

---

## 9. Page structure (DOM order)

```
<head>
  meta tags + OG + Twitter (sec 5)
  Stylesheets (modular: pages.css + page-specific if any)
  JSON-LD blocks in this order: BlogPosting, BreadcrumbList, FAQPage, HowTo (if applicable)
  GA snippet (last)
</head>
<body>
  grain-overlay, cursor, scroll-progress
  Sticky sidebar actions (share, light mode)
  <nav> navbar
  <main> with .blog-layout containing:
    <article class="blog-article"> with H1, TL;DR aside, body
    <aside class="blog-article-sidebar"> with discovery-call CTA
  </main>
  <section class="blog-faq"> -- 3-5 numbered Q&A cards (faq_spec.md)
  <section class="blog-related"> -- 3 cards from approved mapping
  Trust strip
  Footer
  Scripts (deferred where possible)
</body>
```

The FAQ section sits BETWEEN `</article></aside></div>` (closing `.blog-layout`) and `<section class="blog-related">`. No exceptions.

---

## 10. Quality gates (auto-run by validator)

The build pipeline (`scripts/generate_blog.py`) rejects a post if any of these fail:

| Gate | Rule |
|---|---|
| FAQ HTML present | `<section class="blog-faq"` exists |
| FAQ schema present | `"@type": "FAQPage"` exists |
| FAQ count | 3-5 `<details class="blog-faq__item">` items |
| BlogPosting schema | parses, has all required fields |
| Banned vocab | no occurrences of words in `writing_style.md` banned list |
| Em/en dashes | none in body (auto-replaced with hyphens) |
| Meta description | <= 160 chars, non-empty |
| Hero image exists | file at `assets/images/blog/blog-<slug>.webp` |
| Slug uniqueness | not already in `blog/` |
| Internal links | >= 3 in-body links to SARVAYA pages |
| Outbound links | >= 2 links to whitelisted authority domains |

To extend the validator, edit the `# Quality gates` section in `generate_blog.py`. Every new gate added here must also be added to this spec.

---

## 11. Pre-flight checklist (before pushing a manual post)

- [ ] `BlogPosting`, `BreadcrumbList`, `FAQPage` schemas present and parse
- [ ] `HowTo` schema present iff post has sequential steps (sec 1.4)
- [ ] FAQ block has 3-5 questions, 1 internal link inside an answer
- [ ] >= 3 in-body internal links to SARVAYA pages
- [ ] >= 2 outbound links to authority domains, with `rel="noopener noreferrer"`
- [ ] Hero image exists at `blog-<slug>.webp`, 1200x630
- [ ] All `<img>` tags have alt, width, height, loading attrs
- [ ] Meta + OG + Twitter tags complete (sec 5)
- [ ] Slug added to `sitemap.xml`
- [ ] Post linked from `blog.html` index
- [ ] No banned vocabulary, no em-dashes
- [ ] Body 1200-1600 words
- [ ] First 100 words contain primary keyword + a concrete claim
- [ ] At least one bulleted list, one blockquote, one TL;DR aside
- [ ] H2 sections each open with a direct-answer paragraph
- [ ] `dateModified >= datePublished`

Run `python scripts/validate_post.py blog/<slug>.html` (when implemented) to auto-check everything above.

---

## 12. Why each rule exists (do not delete rules without updating this section)

| Rule | Signal it serves |
|---|---|
| FAQPage schema | AEO (PAA), GEO (AI Overviews citations) |
| HowTo schema | Rich result + GEO citation for procedural queries |
| BlogPosting + BreadcrumbList | Core SEO indexation + sitelinks |
| Direct-answer first sentences | GEO passage-level citation pickup |
| Outbound authority links | GEO trust signal (cited content gets cited) |
| Internal links | Topical authority + crawl depth + dwell time |
| Entity density (named tools, dates) | LLM retrieval relevance scoring |
| Banned vocab | Avoid Google AI-content detection penalties |
| TL;DR aside | Highest-cited section for ChatGPT/Perplexity |
| Comparison table / stats callout | Higher AI Overview pickup vs prose |
| Image alt + WebP + dims | Image SERPs + Core Web Vitals (CLS) |
| Hero 1200x630 | Required dimensions for OG previews |
| Schema-content match | Avoid Google's schema-spam penalty (rich result loss) |

If a rule no longer serves a signal, delete it - dead rules cause drift. If a new signal appears, add a rule and a row here in the same commit.
