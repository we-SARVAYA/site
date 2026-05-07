# SARVAYA Blog Writing Rules

These rules are loaded into every blog-generation prompt. Edit this file to change voice without touching Python.

## Punctuation

- **No em dashes (—) or en dashes (–) anywhere.** The pipeline auto-replaces any that slip through with " - " (space-hyphen-space), matching the site's existing title style ("SEO in 2026 - What Actually Works Now"). Still prefer periods, commas, or parentheses when you can restructure the sentence.
- **No rhetorical dashes for drama.** If the sentence needs emphasis, rewrite it.
- Use straight quotes, not curly smart quotes.
- Avoid semicolons. Break into two sentences.

## Banned vocabulary (AI-slop words)

Never use any of these. If one fits the meaning, rewrite the sentence:

delve, delving, leverage, leveraging, utilize, utilise, landscape (as metaphor), tapestry, navigate (as abstract verb), unleash, unlock (as metaphor), realm, journey (as metaphor), dive in, dive into, in today's world, in the digital age, in the modern era, revolutionize, revolutionise, game-changer, game changer, cutting-edge, bleeding-edge, state-of-the-art, seamless, seamlessly, robust (unless literal), synergy, synergies, paradigm, paradigm shift, holistic, empower, empowering, pivotal, foster, fostering, embark, harness, harnessing, spearhead, elevate, elevating, bespoke, curated, meticulously, meticulous, testament, testament to, ever-evolving, rapidly evolving, fast-paced, dynamic (as filler), transformative, disruption, disruptive, thought leader, thought leadership, mission-critical, best-in-class, world-class, next-level, next-gen (unless literal), supercharge, unlock the power, take it to the next level, at the forefront, at the intersection, resonate, resonates, align, alignment (unless literal), streamline, streamlined (unless literal), ecosystem (unless literal), deep dive, crucial (replace with "important" or cut), vital (replace), plethora, myriad, navigate the complexities, the world of, it's worth noting, it is important to note, it goes without saying, needless to say, in conclusion, to sum up, at the end of the day, when it comes to.

## Banned constructions

- **"It's not just X, it's Y."** Never use this rhetorical pattern.
- **"Not only... but also..."** Rewrite directly.
- **"X is more than just Y."** Banned.
- **"In a world where..."** Banned opener.
- **Rhetorical questions as headings.** Headings should be statements or noun phrases.
- **"Let's explore..."**, **"Let's dive into..."**, **"Let's take a look..."** Banned openers for sections.
- **Trailing summary paragraphs that restate what was said.** Stop when the argument is done.
- **Hype adjectives stacked two or three deep** ("powerful, revolutionary, transformative..."). Cut to one concrete adjective or none.

## Voice

- **Confident and direct.** Say the thing. No hedging with "perhaps", "arguably", "some might say".
- **Specific over abstract.** Numbers, named tools, real examples. If you can't name it, cut it.
- **First-person plural (we) allowed sparingly** when referring to SARVAYA as the agency. Never "I".
- **Address the reader as "you"** when giving practical guidance.
- **Active voice.** "Google rewards this" not "This is rewarded by Google".
- **Short sentences win.** Average 12-18 words. Every paragraph should have at least one short punch sentence under 10 words.

## Structure

- Open with a concrete stat, quote, or counter-intuitive fact. No "In today's..." openers.
- One idea per paragraph. 2-4 sentences max.
- H2 sections are statements of fact or clear promises, not questions.
- H3 only when an H2 section needs sub-points.
- Bulleted lists for parallel items (3-6 bullets). Each bullet starts with a bold lead-in followed by the explanation.
- At least one blockquote pulling a strong line from the body.
- Include 2-3 in-body internal links to relevant SARVAYA pages (portfolio, 24hrs, whitelabel, contact, or other blog posts).
- End on the conclusion itself. Do not add "In conclusion" or "To wrap up".

## SEO requirements (non-negotiable)

- Primary keyword in: title, H1, meta description, first 100 words, URL slug, at least one H2.
- Meta description under 160 characters, includes primary keyword, includes a number or specific claim.
- Keywords meta tag lists 5-7 real search terms, not synonyms stuffed together.
- Internal links use descriptive anchor text, never "click here" or "this article".
- One external link to a high-authority source (Google, Anthropic, research study) when citing a fact, with `rel="noopener noreferrer"` if `target="_blank"`.
- Alt text on every image describes the image, includes the primary keyword naturally.

## FAQ requirements (non-negotiable - see faq_spec.md for full rules)

Every post MUST end with an FAQ section between the article body and the "More from our blog" section. The FAQ section must include:

- **3-5 questions** (5 is the sweet spot, never more).
- Questions phrased as a real user would type into Google or ChatGPT (not paraphrased H2s from the article body).
- **40-100 word answers**, first sentence directly answering the question.
- At least one answer with an internal link to a SARVAYA service page or related blog post.
- A matching `FAQPage` JSON-LD schema block in `<head>` whose questions and answers exactly match the visible FAQ.
- Visible markup uses `<details>/<summary>` with `.blog-faq__item / .blog-faq__q / .blog-faq__a` classes.

**The FAQ is structurally mandatory** - posts without it will be rejected by the build validator. Copy the FAQ structure from the reference post (`seo-in-2026.html`) and replace only the question/answer content with topic-specific copy.

## Examples

**Bad:** "In today's rapidly evolving digital landscape, it's more crucial than ever to leverage cutting-edge AI tools to unlock the full potential of your business."

**Good:** "AI search now sends traffic to 12% of Google's top-ranked pages. The other 88% are invisible to ChatGPT, regardless of their rankings."

**Bad:** "We need to delve deep into the tapestry of modern SEO to truly grasp its nuances."

**Good:** "Modern SEO has three inputs: authority signals, technical crawlability, and structured data. Miss any one and rankings collapse."
