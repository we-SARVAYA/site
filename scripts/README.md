# Auto-Publish Pipeline

Publishes one pre-written blog post from the queue every 12 hours. No AI APIs.

## Files

- `publish_next.py` — copies the next queued post from `post_queue/posts/` into `blog/`, patches `blog.html` / `index.html` / `sitemap.xml` / `llms.txt`, and emits commit metadata.
- `rebuild_llms.py` — rebuilds the `## Blog Articles` section of `llms.txt` from current `blog/*.html` files.
- `topics_log.json` — record of past topics (used by `publish_next.py` to update history).
- `post_queue/posts/` — queue of ready-to-publish HTML + WebP pairs.
- `post_queue/archive/` — already-published posts (moved here after publish).
- `post_queue/manifest.json` — queue metadata (slug order, titles, dates).
- `../.github/workflows/daily-blog.yml` — GitHub Actions cron (04:00 + 16:00 UTC).

## How it runs

- **Automatic** — twice a day at 04:00 and 16:00 UTC via GitHub Actions.
- **Manual** — Actions tab → "Auto-publish blog (every 12h)" → Run workflow.

The workflow uses no API keys. Only Gmail SMTP secrets (`GMAIL_USER`, `GMAIL_APP_PASSWORD`, `NOTIFY_EMAIL`) for notification emails.

## Adding new posts to the queue

Write the HTML manually following the structure of any existing post in `post_queue/posts/` or `blog/`. Each queued post needs:

- `post_queue/posts/<slug>.html` — the article HTML, using `{{PUBLISH_DATE}}` / `{{PUBLISH_DATE_HUMAN}}` tokens for date fields (the publisher substitutes them at deploy time).
- `post_queue/posts/<slug>.webp` — the 1200×675 hero image.
- An entry appended to `post_queue/manifest.json` under `posts[]`.

When the queue empties, the workflow sends a "refill needed" email instead of publishing.
