from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any, Iterator

from .config import DB_PATH, DEFAULT_SETTINGS


def utcnow() -> str:
    return datetime.now(UTC).isoformat()


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(DB_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA busy_timeout = 30000")
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS feeds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    enabled INTEGER NOT NULL DEFAULT 1,
    etag TEXT,
    modified TEXT,
    last_checked_at TEXT,
    last_success_at TEXT,
    last_error TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feed_id INTEGER NOT NULL REFERENCES feeds(id) ON DELETE CASCADE,
    guid TEXT,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    author TEXT,
    published_at TEXT,
    summary_html TEXT,
    content_html TEXT,
    image_url TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    error TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    next_retry_at TEXT,
    included_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(feed_id, url)
);
CREATE INDEX IF NOT EXISTS idx_articles_queue ON articles(status, next_retry_at);
CREATE INDEX IF NOT EXISTS idx_articles_edition ON articles(included_at, status, published_at);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    feeds_ok INTEGER NOT NULL DEFAULT 0,
    feeds_failed INTEGER NOT NULL DEFAULT 0,
    articles_ready INTEGER NOT NULL DEFAULT 0,
    articles_failed INTEGER NOT NULL DEFAULT 0,
    edition_id INTEGER,
    error TEXT
);
CREATE TABLE IF NOT EXISTS issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER REFERENCES runs(id) ON DELETE SET NULL,
    feed_id INTEGER REFERENCES feeds(id) ON DELETE SET NULL,
    article_id INTEGER REFERENCES articles(id) ON DELETE SET NULL,
    kind TEXT NOT NULL,
    url TEXT,
    message TEXT NOT NULL,
    resolved_at TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_issues_open ON issues(resolved_at, created_at);
CREATE TABLE IF NOT EXISTS editions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL UNIQUE,
    path TEXT NOT NULL,
    article_count INTEGER NOT NULL,
    status TEXT NOT NULL,
    upload_error TEXT,
    created_at TEXT NOT NULL,
    uploaded_at TEXT
);
"""


def init_db() -> None:
    with connect() as db:
        db.executescript(SCHEMA)
        now = utcnow()
        db.executemany(
            "INSERT OR IGNORE INTO settings(key, value, updated_at) VALUES (?, ?, ?)",
            [(key, json.dumps(value), now) for key, value in DEFAULT_SETTINGS.items()],
        )
        # Migrate the original Russian-only default without overwriting a title
        # that the user deliberately customized.
        db.execute(
            "UPDATE settings SET value=?, updated_at=? WHERE key='edition_title' AND value=?",
            (json.dumps(DEFAULT_SETTINGS["edition_title"]), now, json.dumps("Утренние новости")),
        )


def rows(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with connect() as db:
        return [dict(row) for row in db.execute(sql, params).fetchall()]


def row(sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    result = rows(sql, params)
    return result[0] if result else None


def get_settings() -> dict[str, Any]:
    values = DEFAULT_SETTINGS.copy()
    with connect() as db:
        for record in db.execute("SELECT key, value FROM settings"):
            values[record["key"]] = json.loads(record["value"])
    return values


def save_settings(values: dict[str, Any]) -> dict[str, Any]:
    allowed = set(DEFAULT_SETTINGS)
    now = utcnow()
    with connect() as db:
        db.executemany(
            "INSERT INTO settings(key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            [(key, json.dumps(value), now) for key, value in values.items() if key in allowed],
        )
    return get_settings()


def add_issue(
    kind: str,
    message: str,
    *,
    url: str | None = None,
    run_id: int | None = None,
    feed_id: int | None = None,
    article_id: int | None = None,
) -> None:
    with connect() as db:
        db.execute(
            "INSERT INTO issues(run_id, feed_id, article_id, kind, url, message, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (run_id, feed_id, article_id, kind, url, message[:2000], utcnow()),
        )
