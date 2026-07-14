from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import DEFAULT_SETTINGS, EDITIONS_DIR, ensure_directories
from .db import connect, get_settings, init_db, rows, save_settings, utcnow
from .delivery import authorize_rmapi, reset_rmapi, rmapi_status, test_rmapi, upload_edition
from .pipeline import run_pipeline, run_lock, scheduler_loop


class FeedCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    url: str = Field(min_length=8, max_length=2000)
    enabled: bool = True


class SettingsUpdate(BaseModel):
    values: dict[str, Any]


class AuthCode(BaseModel):
    code: str = Field(min_length=1, max_length=100)


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_directories()
    init_db()
    task = asyncio.create_task(scheduler_loop())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


app = FastAPI(title="Remarkable News", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(packages=[("remarkable_news", "static")]), name="static")


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    path = Path(__file__).with_name("static") / "index.html"
    return HTMLResponse(path.read_text(encoding="utf-8"))


@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "running": run_lock.locked()}


@app.get("/api/dashboard")
def dashboard() -> dict[str, object]:
    with connect() as db:
        counts = {
            "feeds": db.execute("SELECT COUNT(*) FROM feeds WHERE enabled=1").fetchone()[0],
            "pending": db.execute("SELECT COUNT(*) FROM articles WHERE status IN ('pending','failed')").fetchone()[0],
            "dead": db.execute("SELECT COUNT(*) FROM articles WHERE status='dead'").fetchone()[0],
            "open_issues": db.execute("SELECT COUNT(*) FROM issues WHERE resolved_at IS NULL").fetchone()[0],
            "editions": db.execute("SELECT COUNT(*) FROM editions").fetchone()[0],
        }
    return {
        "counts": counts,
        "running": run_lock.locked(),
        "runs": rows("SELECT * FROM runs ORDER BY id DESC LIMIT 10"),
        "rmapi": rmapi_status(),
    }


@app.get("/api/feeds")
def list_feeds() -> list[dict[str, Any]]:
    return rows("SELECT * FROM feeds ORDER BY name COLLATE NOCASE")


@app.post("/api/feeds", status_code=201)
def create_feed(feed: FeedCreate) -> dict[str, Any]:
    parsed = urlparse(feed.url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(422, "Нужен корректный HTTP(S) URL")
    try:
        with connect() as db:
            cursor = db.execute(
                "INSERT INTO feeds(name, url, enabled, created_at) VALUES (?, ?, ?, ?)",
                (feed.name.strip(), feed.url.strip(), int(feed.enabled), utcnow()),
            )
            feed_id = int(cursor.lastrowid)
    except Exception as exc:
        if "UNIQUE" in str(exc):
            raise HTTPException(409, "Эта лента уже добавлена") from exc
        raise
    return rows("SELECT * FROM feeds WHERE id=?", (feed_id,))[0]


@app.patch("/api/feeds/{feed_id}")
def update_feed(feed_id: int, feed: FeedCreate) -> dict[str, Any]:
    with connect() as db:
        cursor = db.execute(
            "UPDATE feeds SET name=?, url=?, enabled=? WHERE id=?",
            (feed.name.strip(), feed.url.strip(), int(feed.enabled), feed_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(404, "Лента не найдена")
    return rows("SELECT * FROM feeds WHERE id=?", (feed_id,))[0]


@app.delete("/api/feeds/{feed_id}", status_code=204, response_class=Response)
def delete_feed(feed_id: int) -> Response:
    with connect() as db:
        db.execute("DELETE FROM feeds WHERE id=?", (feed_id,))
    return Response(status_code=204)


@app.get("/api/settings")
def settings() -> dict[str, Any]:
    return get_settings()


@app.put("/api/settings")
def update_settings(payload: SettingsUpdate) -> dict[str, Any]:
    unknown = set(payload.values) - set(DEFAULT_SETTINGS)
    if unknown:
        raise HTTPException(422, f"Неизвестные настройки: {', '.join(sorted(unknown))}")
    numeric_ranges = {
        "schedule_interval_minutes": (5, 10080), "max_items_per_feed": (1, 200),
        "article_lookback_hours": (1, 720), "request_timeout_seconds": (5, 120),
        "minimum_content_chars": (50, 10000), "max_image_bytes": (100000, 15000000),
        "max_articles_per_edition": (1, 500), "retry_attempts": (1, 20),
        "retry_base_minutes": (1, 1440), "retention_days": (1, 3650),
        "font_size_pt": (7, 24), "line_height": (1.0, 2.5), "page_margin_mm": (5, 35),
    }
    for key, (minimum, maximum) in numeric_ranges.items():
        if key in payload.values:
            try:
                valid = minimum <= float(payload.values[key]) <= maximum
            except (TypeError, ValueError):
                valid = False
            if not valid:
                raise HTTPException(422, f"{key}: допустимо число от {minimum} до {maximum}")
    boolean_keys = {key for key, default in DEFAULT_SETTINGS.items() if isinstance(default, bool)}
    invalid_booleans = [key for key in boolean_keys if key in payload.values and not isinstance(payload.values[key], bool)]
    if invalid_booleans:
        raise HTTPException(422, f"Ожидалось да/нет: {', '.join(sorted(invalid_booleans))}")
    if "paper_size" in payload.values and payload.values["paper_size"] not in {"A4", "A5", "Letter"}:
        raise HTTPException(422, "Допустимый формат бумаги: A4, A5 или Letter")
    if "edition_title" in payload.values:
        title = payload.values["edition_title"]
        if not isinstance(title, str) or not 1 <= len(title.strip()) <= 100:
            raise HTTPException(422, "Название выпуска должно содержать от 1 до 100 символов")
        payload.values["edition_title"] = title.strip()
    if "remarkable_folder" in payload.values:
        folder = payload.values["remarkable_folder"]
        if not isinstance(folder, str) or not folder.startswith("/") or len(folder) > 500 or "\x00" in folder:
            raise HTTPException(422, "Папка reMarkable должна начинаться с / и быть короче 500 символов")
    return save_settings(payload.values)


@app.post("/api/runs", status_code=202)
async def start_run(background: BackgroundTasks) -> dict[str, object]:
    if run_lock.locked():
        raise HTTPException(409, "Сбор уже выполняется")
    background.add_task(run_pipeline, "manual")
    return {"accepted": True}


@app.get("/api/runs")
def list_runs(limit: int = Query(50, ge=1, le=200)) -> list[dict[str, Any]]:
    return rows("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,))


@app.get("/api/issues")
def list_issues(open_only: bool = True, limit: int = Query(100, ge=1, le=500)) -> list[dict[str, Any]]:
    where = "WHERE i.resolved_at IS NULL" if open_only else ""
    return rows(
        f"SELECT i.*, f.name AS feed_name, a.title AS article_title FROM issues i "  # noqa: S608
        f"LEFT JOIN feeds f ON f.id=i.feed_id LEFT JOIN articles a ON a.id=i.article_id {where} "
        "ORDER BY i.id DESC LIMIT ?",
        (limit,),
    )


@app.post("/api/issues/{issue_id}/resolve")
def resolve_issue(issue_id: int) -> dict[str, bool]:
    with connect() as db:
        db.execute("UPDATE issues SET resolved_at=? WHERE id=?", (utcnow(), issue_id))
    return {"success": True}


@app.post("/api/articles/retry")
def retry_failed() -> dict[str, int]:
    with connect() as db:
        cursor = db.execute(
            "UPDATE articles SET status='pending', next_retry_at=NULL WHERE status IN ('failed','dead')"
        )
        count = cursor.rowcount
    return {"queued": count}


@app.get("/api/editions")
def list_editions() -> list[dict[str, Any]]:
    return rows("SELECT * FROM editions ORDER BY id DESC LIMIT 100")


@app.get("/api/editions/{edition_id}/download")
def download_edition(edition_id: int) -> FileResponse:
    result = rows("SELECT * FROM editions WHERE id=?", (edition_id,))
    if not result:
        raise HTTPException(404, "Выпуск не найден")
    path = Path(result[0]["path"])
    if not path.is_file() or path.parent.resolve() != EDITIONS_DIR.resolve():
        raise HTTPException(404, "Файл выпуска отсутствует")
    return FileResponse(path, media_type="application/pdf", filename=result[0]["filename"])


@app.post("/api/editions/{edition_id}/upload")
async def upload(edition_id: int) -> dict[str, bool]:
    return {"success": await upload_edition(edition_id)}


@app.get("/api/rmapi/status")
def get_rmapi_status() -> dict[str, object]:
    return rmapi_status()


@app.post("/api/rmapi/authorize")
async def rmapi_authorize(payload: AuthCode) -> dict[str, object]:
    try:
        return await authorize_rmapi(payload.code)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/rmapi/test")
async def rmapi_test() -> dict[str, object]:
    return await test_rmapi()


@app.post("/api/rmapi/reset")
def rmapi_reset() -> dict[str, bool]:
    reset_rmapi()
    return {"success": True}
