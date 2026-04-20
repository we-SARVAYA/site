# Auto-Blog Pipeline

Publishes one SEO-ready blog post every 12 hours: researches a trending AEO / GEO / Claude / AI-search topic, writes the full HTML, generates a matching hero thumbnail, patches the site index + sitemap + llms.txt, and commits to `main`.

## Files

- `generate_blog.py` — the full pipeline (research → article → thumbnail → patch → commit-ready)
- `requirements.txt` — Python deps (Pillow, requests)
- `topics_log.json` — persistent record of past topics, prevents duplicates
- `../.github/workflows/daily-blog.yml` — GitHub Actions cron (04:00 + 16:00 UTC)

## One-time setup

Add two secrets to the GitHub repo (Settings → Secrets and variables → Actions):

| Secret | Value |
|---|---|
| `ANTHROPIC_API_KEY` | your Claude API key (https://console.anthropic.com) |
| `GEMINI_API_KEY` | your Gemini API key (https://aistudio.google.com/apikey) |

No other config required — `GITHUB_TOKEN` is automatic and the workflow pushes to `main` itself.

## How it runs

- **Automatic** — twice a day at 04:00 and 16:00 UTC.
- **Manual** — Actions tab → "Auto-publish blog (every 12h)" → Run workflow.

## Running locally (dry test)

```bash
# from repo root
pip install -r scripts/requirements.txt
npm install -g @anthropic-ai/claude-code
export ANTHROPIC_API_KEY=sk-ant-...
export GEMINI_API_KEY=AIza...
python scripts/generate_blog.py
```

The script only writes files at the very end; if any step fails, nothing on disk changes.

## Tuning

- **Cadence** — edit the `cron` in `.github/workflows/daily-blog.yml` (UTC).
- **Topic niche** — edit the research prompt in `research_topic()`.
- **Voice / length** — edit the article prompt in `generate_article_html()`.
- **Image style** — edit the prompt builder in `generate_thumbnail()`.
- **Image model** — set env `GEMINI_IMAGE_MODEL` (default `gemini-2.5-flash-image-preview`).
