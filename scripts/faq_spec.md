# Blog Post FAQ Specification

Every blog post on sarvaya.in must include an FAQ section between the article body and the "More from our blog" related-posts section. This document defines the rules. Edit here to change behavior without touching Python.

> **This is a sub-spec.** The master spec covering ALL post-level requirements (every required schema, internal/external linking, AEO/GEO patterns, meta tags, sitemap rules) lives in `scripts/blog_post_spec.md`. Read that first.

## Why FAQs ship on every post

- **GEO (★★★★★)**: AI engines (Google AI Overviews, ChatGPT, Perplexity, Bing Copilot) preferentially cite self-contained Q→A passages. FAQPage schema is one of the strongest GEO signals.
- **AEO (★★★★★)**: Featured snippets and People Also Ask are dominated by Q&A formatted content.
- **Engagement**: Scannable FAQs reduce bounce rate and increase time on page.
- **Long-tail SEO**: Each FAQ question is a chance to rank for a long-tail query the body might miss.
- **Internal linking**: FAQs are natural anchors for cross-links to service pages.

## Hard rules

### 1. Number of questions
- Minimum: **3**
- Maximum: **5**
- Sweet spot: **5**
- More than 5 dilutes quality and risks Google flagging low-effort content.

### 2. Question selection
Every question must be:
- **A real long-tail query** someone would actually type into Google or ask an AI engine. Source from:
  - Google's "People Also Ask" for the post's primary keyword
  - AnswerThePublic
  - Top SERPs for the topic
  - Customer support inbox / sales-call objections
- **Different from any H2 in the article body.** If the body already answers "what is X" in section 2, do not FAQ "what is X". Instead FAQ "is X better than Y" or "how do I get started with X".
- **Phrased as the user would phrase it.** Use "How do I..." not "How does one...". Use "What is..." not "Defining...".
- **Specific to this post's topic.** No generic agency FAQs ("how much does it cost", "do you offer support") - those belong on the homepage and service pages.

### 3. Answer length and structure
- **40-100 words per answer.** Short enough to be lifted as a featured snippet, long enough to actually answer.
- **First sentence must directly answer the question.** No throat-clearing ("That's a great question...").
- **One claim per paragraph.** Multiple paragraphs allowed if the answer needs them, but each paragraph must stand alone.
- **Concrete specifics.** Numbers, dates, named tools, percentages where possible.
- **No banned vocabulary** (see `writing_style.md`).

### 4. Schema requirement
Every post must include a `FAQPage` JSON-LD block in `<head>` matching the visible FAQ section verbatim.

```html
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": [
        {
            "@type": "Question",
            "name": "Question text exactly as shown on page",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "Answer text - plain text only, no HTML. Should match the visible answer."
            }
        }
    ]
}
</script>
```

### 5. Visible markup
Use semantic `<details>/<summary>` for native accordion (zero JS dependency). The CSS class hooks are already in `pages.css`:

```html
<section class="blog-faq" aria-labelledby="blog-faq-heading">
    <div class="container">
        <div class="blog-faq__label">Common Questions</div>
        <h2 id="blog-faq-heading" class="blog-faq__title">Frequently Asked Questions</h2>
        <div class="blog-faq__list">
            <details class="blog-faq__item">
                <summary class="blog-faq__q"><span class="blog-faq__q-text">Question text</span></summary>
                <div class="blog-faq__a">
                    <p>Answer text.</p>
                </div>
            </details>
            <!-- repeat 2-4 more times -->
        </div>
    </div>
</section>
```

### 6. Position
The FAQ section sits between the closing `</div>` of `.blog-layout` and the opening `<section class="blog-related">` of "More from our blog".

### 7. Internal linking
At least **one FAQ answer** should contain an internal link to a relevant SARVAYA service page (`/services/web-development`, `/services/ai-automation`, `/services/seo-geo`, `/whitelabel`, `/24hrs`, `/contact`) or a related blog post. Use descriptive anchor text.

## Anti-patterns (rejection-worthy)

- ❌ Asking "What does SARVAYA do?" - that's not what the post is about
- ❌ Asking the same question the H1 or H2s already answer
- ❌ Asking yes/no questions without the answer expanding the topic
- ❌ Generic pricing or contact questions on a topical post
- ❌ Single-sentence answers under 30 words
- ❌ Multi-paragraph answers over 150 words
- ❌ Mismatched schema and visible content (Google penalizes this)
- ❌ Using `<button>` or custom JS accordions instead of `<details>`
- ❌ Wrapping the FAQ in `<aside>` or sidebar - it must be full-width

## Reference implementation

See either of these posts for a working example:
- `blog/seo-in-2026.html` (the LLM reference template)
- `blog/ai-citations-vs-google-rankings-geo-strategy.html` (early example post)

Both follow this spec exactly. New posts generated via `scripts/generate_blog.py` will copy this structure automatically.
