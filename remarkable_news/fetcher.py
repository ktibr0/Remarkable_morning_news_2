from __future__ import annotations

import asyncio
import hashlib
import re
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urljoin

import bleach
import feedparser
import httpx
import trafilatura
from lxml import html as lxml_html

from .db import add_issue, connect, get_settings, utcnow


ALLOWED_TAGS = [
    "p", "br", "h2", "h3", "h4", "blockquote", "pre", "code", "ul", "ol", "li",
    "strong", "b", "em", "i", "a", "figure", "figcaption", "img", "hr", "table",
    "thead", "tbody", "tr", "th", "td",
]
ALLOWED_ATTRIBUTES = {
    "a": ["href", "title"],
    "img": ["src", "alt", "title"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan"],
}
USER_AGENT = "RemarkableNews/0.1 (+self-hosted RSS reader)"


def clean_html(value: str | None, base_url: str, *, images: bool) -> str:
    if not value:
        return ""
    tags = ALLOWED_TAGS if images else [tag for tag in ALLOWED_TAGS if tag not in {"img", "figure"}]
    cleaned = bleach.clean(
        value,
        tags=tags,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=["http", "https", "data"],
        strip=True,
    )
    try:
        root = lxml_html.fragment_fromstring(cleaned, create_parent=True)
        for element in root.xpath(".//*[@href]"):
            element.set("href", urljoin(base_url, element.get("href")))
        for element in root.xpath(".//*[@src]"):
            element.set("src", urljoin(base_url, element.get("src")))
        return "".join(lxml_html.tostring(child, encoding="unicode") for child in root)
    except (ValueError, TypeError):
        return cleaned


def text_length(value: str | None) -> int:
    if not value:
        return 0
    return len(re.sub(r"\s+", " ", bleach.clean(value, tags=[], strip=True)).strip())


def entry_url(entry: Any) -> str:
    return str(entry.get("link") or entry.get("id") or "").strip()


def entry_content(entry: Any) -> str:
    content = entry.get("content") or []
    if content and isinstance(content, list):
        return str(content[0].get("value") or "")
    return str(entry.get("summary") or entry.get("description") or "")


def entry_date(entry: Any) -> str | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        return datetime(*parsed[:6], tzinfo=UTC).isoformat()
    raw = entry.get("published") or entry.get("updated")
    if raw:
        try:
            return parsedate_to_datetime(raw).astimezone(UTC).isoformat()
        except (TypeError, ValueError, OverflowError):
            pass
    return None


def discover_image(entry: Any, content: str) -> str | None:
    for field in ("media_content", "media_thumbnail"):
        media = entry.get(field) or []
        if media and media[0].get("url"):
            return str(media[0]["url"])
    for enclosure in entry.get("enclosures") or []:
        if str(enclosure.get("type", "")).startswith("image/"):
            return str(enclosure.get("href") or enclosure.get("url") or "") or None
    match = re.search(r"<img[^>]+src=[\"']([^\"']+)", content, re.I)
    return match.group(1) if match else None


def stable_url(entry: Any, feed_url: str) -> str:
    candidate = entry_url(entry)
    if candidate:
        return urljoin(feed_url, candidate)
    seed = f"{entry.get('id', '')}|{entry.get('title', '')}|{entry.get('published', '')}"
    return f"urn:rss:{hashlib.sha256(seed.encode()).hexdigest()}"


async def fetch_feed(client: httpx.AsyncClient, feed: dict[str, Any], run_id: int) -> tuple[int, int]:
    settings = get_settings()
    headers: dict[str, str] = {}
    if feed.get("etag"):
        headers["If-None-Match"] = feed["etag"]
    if feed.get("modified"):
        headers["If-Modified-Since"] = feed["modified"]
    now = utcnow()
    try:
        response = await client.get(feed["url"], headers=headers)
        if response.status_code == 304:
            with connect() as db:
                db.execute("UPDATE feeds SET last_checked_at=?, last_success_at=?, last_error=NULL WHERE id=?", (now, now, feed["id"]))
                db.execute(
                    "UPDATE issues SET resolved_at=? WHERE feed_id=? AND kind='feed_error' AND resolved_at IS NULL",
                    (now, feed["id"]),
                )
            return (1, 0)
        response.raise_for_status()
        parsed = await asyncio.to_thread(feedparser.parse, response.content)
        if not parsed.entries:
            detail = str(getattr(parsed, "bozo_exception", "лента не содержит записей"))
            raise ValueError(f"RSS не содержит читаемых записей: {detail}")
        warning = str(getattr(parsed, "bozo_exception", "")) if parsed.bozo else None
        with connect() as db:
            db.execute(
                "UPDATE feeds SET etag=?, modified=?, last_checked_at=?, last_success_at=?, last_error=? WHERE id=?",
                (response.headers.get("etag"), response.headers.get("last-modified"), now, now, warning, feed["id"]),
            )
            db.execute(
                "UPDATE issues SET resolved_at=? WHERE feed_id=? AND kind='feed_error' AND resolved_at IS NULL",
                (now, feed["id"]),
            )
            if not warning:
                db.execute(
                    "UPDATE issues SET resolved_at=? WHERE feed_id=? AND kind='feed_warning' AND resolved_at IS NULL",
                    (now, feed["id"]),
                )
        if warning:
            add_issue("feed_warning", warning, url=feed["url"], run_id=run_id, feed_id=feed["id"])
        limit = int(settings["max_items_per_feed"])
        cutoff = datetime.now(UTC) - timedelta(hours=int(settings["article_lookback_hours"]))
        for entry in parsed.entries[:limit]:
            published = entry_date(entry)
            if published and datetime.fromisoformat(published) < cutoff:
                continue
            raw = entry_content(entry)
            url = stable_url(entry, feed["url"])
            title = str(entry.get("title") or "Без заголовка").strip()
            image = discover_image(entry, raw)
            if image:
                image = urljoin(url if url.startswith("http") else feed["url"], image)
            with connect() as db:
                db.execute(
                    "INSERT INTO articles(feed_id, guid, url, title, author, published_at, summary_html, image_url, status, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?) "
                    "ON CONFLICT(feed_id, url) DO UPDATE SET title=excluded.title, author=excluded.author, "
                    "published_at=COALESCE(excluded.published_at, articles.published_at), summary_html=excluded.summary_html, "
                    "image_url=COALESCE(excluded.image_url, articles.image_url), updated_at=excluded.updated_at",
                    (feed["id"], str(entry.get("id") or ""), url, title, str(entry.get("author") or ""), published, raw, image, now, now),
                )
        return (1, 0)
    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        with connect() as db:
            db.execute("UPDATE feeds SET last_checked_at=?, last_error=? WHERE id=?", (now, message[:2000], feed["id"]))
        add_issue("feed_error", message, url=feed["url"], run_id=run_id, feed_id=feed["id"])
        return (0, 1)


async def extract_article(client: httpx.AsyncClient, article: dict[str, Any], run_id: int) -> bool:
    settings = get_settings()
    minimum = int(settings["minimum_content_chars"])
    include_images = bool(settings["include_images"])
    rss_html = clean_html(article.get("summary_html"), article["url"], images=include_images)
    selected = rss_html
    error: str | None = None
    should_fetch = bool(settings["prefer_full_article"]) or text_length(rss_html) < minimum
    if should_fetch and article["url"].startswith(("http://", "https://")):
        try:
            response = await client.get(article["url"])
            response.raise_for_status()
            extracted = await asyncio.to_thread(
                trafilatura.extract,
                response.text,
                output_format="html",
                include_links=True,
                include_images=include_images,
                include_tables=True,
                favor_recall=True,
                url=article["url"],
            )
            extracted_clean = clean_html(extracted, article["url"], images=include_images)
            if text_length(extracted_clean) >= max(minimum, text_length(rss_html)):
                selected = extracted_clean
            elif text_length(rss_html) < minimum:
                error = "полный текст не извлечён, а содержимое RSS слишком короткое"
        except Exception as exc:
            error = f"не удалось получить страницу: {type(exc).__name__}: {exc}"
    if text_length(selected) < minimum:
        error = error or f"полезного текста меньше {minimum} символов"
    now = datetime.now(UTC)
    if error:
        attempts = int(article["attempts"]) + 1
        max_attempts = int(settings["retry_attempts"])
        terminal = attempts >= max_attempts
        delay = int(settings["retry_base_minutes"]) * (2 ** min(attempts - 1, 6))
        next_retry = None if terminal else (now + timedelta(minutes=delay)).isoformat()
        with connect() as db:
            db.execute(
                "UPDATE articles SET status=?, error=?, attempts=?, next_retry_at=?, updated_at=? WHERE id=?",
                ("dead" if terminal else "failed", error[:2000], attempts, next_retry, now.isoformat(), article["id"]),
            )
        add_issue("article_error", error, url=article["url"], run_id=run_id, feed_id=article["feed_id"], article_id=article["id"])
        return False
    with connect() as db:
        db.execute(
            "UPDATE articles SET status='ready', content_html=?, error=NULL, next_retry_at=NULL, updated_at=? WHERE id=?",
            (selected, now.isoformat(), article["id"]),
        )
        db.execute("UPDATE issues SET resolved_at=? WHERE article_id=? AND resolved_at IS NULL", (now.isoformat(), article["id"]))
    return True


async def collect(run_id: int) -> tuple[int, int, int, int]:
    settings = get_settings()
    timeout = httpx.Timeout(float(settings["request_timeout_seconds"]))
    limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)
    async with httpx.AsyncClient(timeout=timeout, limits=limits, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
        with connect() as db:
            feeds = [dict(row) for row in db.execute("SELECT * FROM feeds WHERE enabled=1 ORDER BY id")]
        feed_results = await asyncio.gather(*(fetch_feed(client, feed, run_id) for feed in feeds))
        feeds_ok = sum(result[0] for result in feed_results)
        feeds_failed = sum(result[1] for result in feed_results)
        with connect() as db:
            queued = [dict(row) for row in db.execute(
                "SELECT * FROM articles WHERE status='pending' OR (status='failed' AND next_retry_at<=?) ORDER BY published_at, id",
                (utcnow(),),
            )]
        results = await asyncio.gather(*(extract_article(client, article, run_id) for article in queued))
        return feeds_ok, feeds_failed, sum(results), len(results) - sum(results)
