import asyncio
import sqlite3
from contextlib import contextmanager

import remarkable_news.pipeline as pipeline


def test_pipeline_automatically_uploads_a_new_edition(monkeypatch, tmp_path):
    database = tmp_path / "pipeline.db"
    with sqlite3.connect(database) as db:
        db.execute(
            "CREATE TABLE runs (id INTEGER PRIMARY KEY, trigger TEXT, status TEXT, started_at TEXT, "
            "finished_at TEXT, feeds_ok INTEGER DEFAULT 0, feeds_failed INTEGER DEFAULT 0, "
            "articles_ready INTEGER DEFAULT 0, articles_failed INTEGER DEFAULT 0, edition_id INTEGER, error TEXT)"
        )

    @contextmanager
    def connect():
        connection = sqlite3.connect(database)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    uploaded = []

    async def collect(_run_id):
        return 1, 0, 2, 0

    async def render(_run_id):
        return 42

    async def upload(edition_id, *, run_id=None):
        uploaded.append((edition_id, run_id))
        return True

    monkeypatch.setattr(pipeline, "connect", connect)
    monkeypatch.setattr(pipeline, "collect", collect)
    monkeypatch.setattr(pipeline, "render_edition", render)
    monkeypatch.setattr(pipeline, "upload_edition", upload)
    monkeypatch.setattr(pipeline, "cleanup_retention", lambda: 0)
    monkeypatch.setattr(pipeline, "get_settings", lambda: {"remarkable_enabled": True})

    result = asyncio.run(pipeline.run_pipeline("schedule"))

    assert result["status"] == "success"
    assert result["upload_success"] is True
    assert uploaded == [(42, result["run_id"])]


def test_failed_automatic_upload_marks_run_partial(monkeypatch, tmp_path):
    database = tmp_path / "pipeline.db"
    with sqlite3.connect(database) as db:
        db.execute(
            "CREATE TABLE runs (id INTEGER PRIMARY KEY, trigger TEXT, status TEXT, started_at TEXT, "
            "finished_at TEXT, feeds_ok INTEGER DEFAULT 0, feeds_failed INTEGER DEFAULT 0, "
            "articles_ready INTEGER DEFAULT 0, articles_failed INTEGER DEFAULT 0, edition_id INTEGER, error TEXT)"
        )

    @contextmanager
    def connect():
        connection = sqlite3.connect(database)
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    async def collect(_run_id):
        return 1, 0, 1, 0

    async def render(_run_id):
        return 7

    async def upload(_edition_id, *, run_id=None):
        return False

    monkeypatch.setattr(pipeline, "connect", connect)
    monkeypatch.setattr(pipeline, "collect", collect)
    monkeypatch.setattr(pipeline, "render_edition", render)
    monkeypatch.setattr(pipeline, "upload_edition", upload)
    monkeypatch.setattr(pipeline, "cleanup_retention", lambda: 0)
    monkeypatch.setattr(pipeline, "get_settings", lambda: {"remarkable_enabled": True})

    result = asyncio.run(pipeline.run_pipeline("schedule"))

    assert result["status"] == "partial"
    assert result["upload_success"] is False
