# Remarkable News

Reliable self-hosted RSS-to-PDF delivery for reMarkable tablets.

This is an actively maintained fork and rewrite of [ktibr0/Remarkable_morning_news](https://github.com/ktibr0/Remarkable_morning_news), which is now archived. The original project used an n8n workflow; this version turns the idea into a standalone web application with persistent storage, retry logic, PDF archiving, image embedding, and direct delivery to reMarkable Cloud through [ddvk/rmapi](https://github.com/ddvk/rmapi/).

The web UI opens in English by default and can be switched to Russian from the language selector in the top-right corner.

Pipeline:

```text
RSS -> SQLite queue -> article extraction and validation -> HTML -> Gotenberg -> PDF archive -> rmapi
```

A broken feed, article, or image does not cancel the whole run. Failed URLs are logged, retried with backoff, and can be manually returned to the queue. Each PDF is built only from articles that passed the content checks.

## Features

- Web dashboard for RSS feeds, scheduling, PDF layout, saved editions, logs, and reMarkable delivery.
- English and Russian UI.
- ETag and Last-Modified support for efficient RSS polling.
- Graceful handling of partially malformed RSS feeds.
- Full-text extraction with Trafilatura when RSS entries only contain short previews.
- Minimum useful text length checks and article states: `pending`, `failed`, `dead`, `ready`.
- Exponential retries and manual retry for failed URLs.
- Precise issue log with URL, source, and failure reason.
- Lead image discovery, local image cache, and image embedding into generated PDFs.
- PDF archive with configurable retention.
- Manual re-upload of any saved edition.
- Optional automatic upload to reMarkable Cloud after scheduled and manual builds.
- SQLite in WAL mode, persistent `./data` folder next to the project, and a non-root application user.
- Multi-stage Docker image with pinned dependencies and a pinned rmapi build.
- Lightweight `gotenberg/gotenberg:8-chromium` service without LibreOffice.

## Quick Start

Requirements:

- Docker Engine with Compose v2.
- Internet access from the server.

```bash
docker compose build
docker compose up -d
```

Open the web UI:

```text
http://<server-ip>:8000
```

Add RSS feeds on the Feeds tab, tune collection and PDF settings on Layout & collection, then click Build edition.

## reMarkable Setup

1. Open the reMarkable tab.
2. Follow the one-time-code link.
3. Paste the code into the form and click Connect.
4. The app verifies the connection by making a real cloud request.
5. Set the target folder, for example `/News`.
6. Enable Automatically send editions if you want every completed edition uploaded to reMarkable Cloud.

If old or damaged rmapi tokens remain in the config volume, use Reset tokens and authorize again with a fresh one-time code.

rmapi credentials are stored in the Docker volume `remarkable-news_rmapi_config`. They are not stored in the SQLite database, not copied into the image, and must never be committed to Git.

## Storage and Backups

Runtime files are intentionally kept outside the image:

- `./data`: SQLite database, PDFs, cached images, and logs (`news.db`, `editions/`, `images/`, `logs/`).
- `remarkable-news_rmapi_config`: rmapi cloud tokens and local rmapi configuration.

Example backup:

```bash
tar czf remarkable-news-data.tgz -C data .
docker run --rm -v remarkable-news_rmapi_config:/source:ro -v "$PWD":/backup alpine \
  tar czf /backup/remarkable-news-rmapi.tgz -C /source .
```

For a consistent SQLite backup, stop the app before copying and start it again afterwards:

```bash
docker compose stop app
docker compose start app
```

## Recommended Settings

- Minimum useful characters: 300-600. Higher values remove thin pages, but may skip short news posts.
- Retry attempts: 5.
- First retry delay: 15 minutes.
- Look back: 48 hours to avoid importing a very old archive during the first run.
- Images: 3 MB per image. Oversized or unavailable images are skipped.
- Retention: 30 days. Old PDFs and closed old issues are removed; article records remain for deduplication.
- Start each article on a new page: useful for tablet navigation, but produces longer PDFs.

## Operations

```bash
docker compose logs -f app
docker compose ps
docker compose pull gotenberg
docker compose build --pull app
docker compose up -d
```

API documentation is available at `/docs`.

The app is designed for one scheduler and one application process. Do not scale the app service to multiple workers without moving locking and queue ownership out of the process.

## Security

The web dashboard has no built-in user account. It is intended for a trusted home network.

Do not expose port `8000` directly to the internet. For remote access, use a VPN or a reverse proxy with TLS and authentication. Gotenberg is only reachable inside the Docker network.

Keep these files and folders out of Git:

- `.githubtoken`
- `.ssh_creds/`
- `.venv/`
- `data/`
- `config/`
- rmapi config and token files
- generated PDFs and backups

The project `.gitignore` and `.dockerignore` already exclude these paths.

## Diagnostics

Common issue types:

- `feed_error`: a feed could not be loaded or had no readable entries.
- `feed_warning`: feedparser found malformed RSS, but entries were still usable.
- `article_error`: full text could not be extracted and the RSS text was too short.
- `pdf_error`: Gotenberg did not produce a PDF.
- `upload_error`: rmapi failed to upload the PDF.

Full rmapi crash output is written to `/data/logs/rmapi.log` with rotation. The web log only shows the practical failure reason.

Open issues are visible on the Log tab. Retry failed URLs returns both temporary failures and exhausted articles to the queue. Feed errors are retried automatically on the next scheduled run.

## Development

```bash
uv sync --extra dev
uv run ruff check .
uv run pytest
```

Dependencies are locked in `uv.lock`. Docker BuildKit reuses uv and Go build layers where possible.

## Migration from the Original n8n Workflow

The old `Remarkable_news.json` file is kept as a reference.

Suggested migration path:

1. Run this Compose stack on another port or stop the old `rmapi_api` and Gotenberg containers.
2. Add your RSS feeds in the new dashboard.
3. Set interval, per-feed item limits, lookback, and target folder to match the old workflow.
4. Authorize rmapi.
5. Run a manual test build.
6. Check the generated PDF and delivery.
7. Disable the old n8n schedule.
