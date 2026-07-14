from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from .db import connect, get_settings, utcnow
from .delivery import cleanup_retention, render_edition, upload_edition
from .fetcher import collect


run_lock = asyncio.Lock()
last_scheduler_check: datetime | None = None


async def run_pipeline(trigger: str = "manual") -> dict[str, Any]:
    if run_lock.locked():
        return {"accepted": False, "message": "Сбор уже выполняется"}
    async with run_lock:
        started = utcnow()
        with connect() as db:
            cursor = db.execute(
                "INSERT INTO runs(trigger, status, started_at) VALUES (?, 'running', ?)",
                (trigger, started),
            )
            run_id = int(cursor.lastrowid)
        try:
            feeds_ok, feeds_failed, ready, failed = await collect(run_id)
            edition_id = await render_edition(run_id)
            upload_success: bool | None = None
            if edition_id is not None and get_settings()["remarkable_enabled"]:
                upload_success = await upload_edition(edition_id, run_id=run_id)
            cleanup_retention()
            status = "success" if feeds_failed == 0 and failed == 0 else "partial"
            if upload_success is False:
                status = "partial"
            with connect() as db:
                db.execute(
                    "UPDATE runs SET status=?, finished_at=?, feeds_ok=?, feeds_failed=?, articles_ready=?, articles_failed=?, edition_id=? WHERE id=?",
                    (status, utcnow(), feeds_ok, feeds_failed, ready, failed, edition_id, run_id),
                )
            return {
                "accepted": True,
                "run_id": run_id,
                "status": status,
                "edition_id": edition_id,
                "upload_success": upload_success,
            }
        except Exception as exc:
            with connect() as db:
                db.execute(
                    "UPDATE runs SET status='failed', finished_at=?, error=? WHERE id=?",
                    (utcnow(), f"{type(exc).__name__}: {exc}"[:2000], run_id),
                )
            return {"accepted": True, "run_id": run_id, "status": "failed", "error": str(exc)}


async def scheduler_loop() -> None:
    while True:
        try:
            settings = get_settings()
            if settings["schedule_enabled"] and not run_lock.locked():
                with connect() as db:
                    last = db.execute(
                        "SELECT started_at FROM runs WHERE trigger='schedule' ORDER BY id DESC LIMIT 1"
                    ).fetchone()
                due = not last
                if last:
                    interval = timedelta(minutes=int(settings["schedule_interval_minutes"]))
                    due = datetime.fromisoformat(last["started_at"]) + interval <= datetime.now(UTC)
                if due:
                    await run_pipeline("schedule")
        except asyncio.CancelledError:
            raise
        except Exception:
            # The scheduler must survive a corrupted run; the run itself records detailed errors.
            pass
        await asyncio.sleep(30)
