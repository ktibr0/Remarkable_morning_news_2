from __future__ import annotations

import asyncio
import base64
import hashlib
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from jinja2 import Environment, PackageLoader, select_autoescape
from lxml import html as lxml_html

from .config import EDITIONS_DIR, GOTENBERG_URL, IMAGES_DIR, LOGS_DIR, RMAPI_CONFIG
from .db import add_issue, connect, get_settings, utcnow


templates = Environment(
    loader=PackageLoader("remarkable_news", "templates"),
    autoescape=select_autoescape(["html", "xml"]),
)


@dataclass(frozen=True)
class RmapiResult:
    success: bool
    output: str
    raw_output: str
    returncode: int | None


def summarize_rmapi_output(output: str, limit: int = 2000) -> str:
    """Keep the useful error and discard the repetitive Go runtime worker dump."""
    cleaned = re.sub(r"\x1b\[[0-9;]*m", "", output).strip()
    if not cleaned:
        return "rmapi не сообщил подробностей"
    lines = cleaned.splitlines()
    important = []
    for line in lines:
        lower = line.lower()
        if any(marker in lower for marker in (
            "fatal error:", "panic:", "error:", "failed", "auth:",
            "permission denied", "no such file", "unauthorized", "forbidden",
        )):
            important.append(line.strip())
    # The beginning contains the panic reason and goroutine 1; later GC workers are noise.
    head = "\n".join(lines[:35])
    diagnostic = "\n".join(dict.fromkeys(important[:12]))
    result = diagnostic
    if head and head not in result:
        result = f"{diagnostic}\n\n{head}" if diagnostic else head
    if len(cleaned) > len(head):
        result += "\n\n[полный дамп сохранён в /data/logs/rmapi.log]"
    return result[:limit]


def write_rmapi_log(command: list[str], output: str) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    path = LOGS_DIR / "rmapi.log"
    if path.exists() and path.stat().st_size > 2_000_000:
        rotated = LOGS_DIR / "rmapi.log.1"
        rotated.unlink(missing_ok=True)
        path.replace(rotated)
    safe_command = " ".join(command)
    with path.open("a", encoding="utf-8") as log:
        log.write(f"\n\n===== {utcnow()} :: {safe_command} =====\n")
        log.write(output[:200_000])


async def run_rmapi(
    arguments: list[str],
    *,
    input_text: str | None = None,
    timeout: int = 90,
) -> RmapiResult:
    env = {
        **os.environ,
        "HOME": str(RMAPI_CONFIG.parent),
        "XDG_CONFIG_HOME": str(RMAPI_CONFIG.parent),
        "XDG_DATA_HOME": str(RMAPI_CONFIG.parent),
        "USERPROFILE": str(RMAPI_CONFIG.parent),
        "RMAPI_CONFIG": str(RMAPI_CONFIG),
        "RMAPI_CONCURRENT": os.getenv("RMAPI_CONCURRENT", "4"),
    }
    command = ["rmapi", *arguments]
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE if input_text is not None else asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=str(RMAPI_CONFIG.parent),
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input_text.encode() if input_text is not None else None),
                timeout=timeout,
            )
        except TimeoutError:
            process.kill()
            await process.wait()
            message = f"rmapi превысил таймаут {timeout} секунд"
            write_rmapi_log(command, message)
            return RmapiResult(False, message, message, None)
        raw = "\n".join(
            part.decode(errors="replace").strip() for part in (stderr, stdout) if part
        ).strip()
        if process.returncode != 0:
            write_rmapi_log(command, raw)
        return RmapiResult(
            process.returncode == 0,
            summarize_rmapi_output(raw) if process.returncode != 0 else raw[-2000:],
            raw,
            process.returncode,
        )
    except OSError as exc:
        message = f"Не удалось запустить rmapi: {exc}"
        write_rmapi_log(command, message)
        return RmapiResult(False, message, message, None)


def _image_mime(content_type: str, payload: bytes) -> str | None:
    declared = content_type.split(";", 1)[0].strip().lower()
    if declared.startswith("image/"):
        return declared
    signatures = (
        (b"\xff\xd8\xff", "image/jpeg"),
        (b"\x89PNG\r\n\x1a\n", "image/png"),
        (b"GIF87a", "image/gif"),
        (b"GIF89a", "image/gif"),
        (b"RIFF", "image/webp"),
    )
    for signature, mime in signatures:
        if payload.startswith(signature):
            if mime != "image/webp" or payload[8:12] == b"WEBP":
                return mime
    return None


def _add_lead_image(content: str, image_url: str | None) -> str:
    if not image_url:
        return content
    try:
        root = lxml_html.fragment_fromstring(content or "", create_parent=True)
        if root.xpath(".//img[@src]"):
            return content
        figure = lxml_html.Element("figure")
        image = lxml_html.Element("img", src=image_url, alt="")
        figure.append(image)
        root.insert(0, figure)
        return "".join(lxml_html.tostring(child, encoding="unicode") for child in root)
    except (ValueError, TypeError):
        return content


async def embed_images(
    content: str,
    client: httpx.AsyncClient,
    max_bytes: int,
    *,
    referer: str | None = None,
) -> str:
    try:
        root = lxml_html.fragment_fromstring(content, create_parent=True)
    except (ValueError, TypeError):
        return content
    for image in root.xpath(".//img[@src]"):
        source = image.get("src", "")
        if not source.startswith(("http://", "https://")):
            continue
        try:
            headers = {"Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"}
            if referer and referer.startswith(("http://", "https://")):
                headers["Referer"] = referer
            response = await client.get(source, headers=headers)
            response.raise_for_status()
            payload = response.content
            mime = _image_mime(response.headers.get("content-type", ""), payload)
            if not mime or len(payload) > max_bytes:
                image.drop_tree()
                continue
            suffix = {"image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif", "image/webp": ".webp"}.get(mime, ".img")
            cache_path = IMAGES_DIR / f"{hashlib.sha256(source.encode()).hexdigest()}{suffix}"
            cache_path.write_bytes(payload)
            encoded = base64.b64encode(payload).decode("ascii")
            image.set("src", f"data:{mime};base64,{encoded}")
            for attribute in ("srcset", "loading", "style", "width", "height"):
                image.attrib.pop(attribute, None)
        except Exception:
            image.drop_tree()
    return "".join(lxml_html.tostring(child, encoding="unicode") for child in root)


async def render_edition(run_id: int) -> int | None:
    settings = get_settings()
    with connect() as db:
        articles = [dict(row) for row in db.execute(
            "SELECT a.*, f.name AS feed_name FROM articles a JOIN feeds f ON f.id=a.feed_id "
            "WHERE a.status='ready' AND a.included_at IS NULL ORDER BY COALESCE(a.published_at, a.created_at), a.id LIMIT ?",
            (int(settings["max_articles_per_edition"]),),
        )]
    if not articles and not settings["create_empty_editions"]:
        return None

    if settings["include_images"]:
        timeout = httpx.Timeout(float(settings["request_timeout_seconds"]))
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            for article in articles:
                article["content_html"] = _add_lead_image(article["content_html"], article.get("image_url"))
                article["content_html"] = await embed_images(
                    article["content_html"], client, int(settings["max_image_bytes"]), referer=article.get("url")
                )
    else:
        for article in articles:
            try:
                root = lxml_html.fragment_fromstring(article["content_html"], create_parent=True)
                for image in root.xpath(".//img|.//figure"):
                    image.drop_tree()
                article["content_html"] = "".join(lxml_html.tostring(child, encoding="unicode") for child in root)
            except (ValueError, TypeError):
                pass

    generated_at = datetime.now().astimezone()
    document = templates.get_template("edition.html").render(
        articles=articles,
        settings=settings,
        generated_at=generated_at,
    )
    filename = f"news_{generated_at:%Y-%m-%d_%H-%M-%S}_run-{run_id}.pdf"
    path = EDITIONS_DIR / filename
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{GOTENBERG_URL}/forms/chromium/convert/html",
                files={"files": ("index.html", document.encode("utf-8"), "text/html")},
                data={
                    "preferCssPageSize": "true",
                    "printBackground": "true",
                    "generateDocumentOutline": "true",
                    "failOnResourceLoadingFailed": "true",
                },
            )
            response.raise_for_status()
            path.write_bytes(response.content)
    except Exception as exc:
        add_issue("pdf_error", f"Gotenberg: {type(exc).__name__}: {exc}", run_id=run_id)
        raise

    now = utcnow()
    with connect() as db:
        cursor = db.execute(
            "INSERT INTO editions(filename, path, article_count, status, created_at) VALUES (?, ?, ?, 'created', ?)",
            (filename, str(path), len(articles), now),
        )
        edition_id = int(cursor.lastrowid)
        if articles:
            placeholders = ",".join("?" for _ in articles)
            db.execute(
                f"UPDATE articles SET included_at=? WHERE id IN ({placeholders})",  # noqa: S608
                (now, *(article["id"] for article in articles)),
            )
    return edition_id


def rmapi_status() -> dict[str, object]:
    configured = RMAPI_CONFIG.exists() and RMAPI_CONFIG.stat().st_size > 20
    return {"configured": configured, "config_path": str(RMAPI_CONFIG)}


def reset_rmapi() -> None:
    RMAPI_CONFIG.unlink(missing_ok=True)


async def authorize_rmapi(code: str) -> dict[str, object]:
    if not code.strip() or len(code.strip()) > 100:
        raise ValueError("Некорректный одноразовый код")
    RMAPI_CONFIG.touch(mode=0o600, exist_ok=True)
    # `rmapi version` is offline and never authenticates. A real cloud command both
    # consumes the one-time code and proves that the resulting tokens work.
    result = await run_rmapi(["-json", "ls", "/"], input_text=f"{code.strip()}\n", timeout=120)
    if not result.success:
        raise RuntimeError(result.output)
    if not RMAPI_CONFIG.exists() or RMAPI_CONFIG.stat().st_size <= 20:
        raise RuntimeError("rmapi ответил успешно, но не сохранил токены авторизации")
    return {
        "success": True,
        "output": "Авторизация сохранена, список документов reMarkable Cloud получен.",
    }


async def test_rmapi() -> dict[str, object]:
    if not rmapi_status()["configured"]:
        return {"success": False, "output": "Токены отсутствуют. Получите новый одноразовый код."}
    result = await run_rmapi(["-ni", "-json", "ls", "/"], timeout=120)
    return {
        "success": result.success,
        "output": (
            "Подключение работает: reMarkable Cloud доступен."
            if result.success else result.output
        ),
    }


async def upload_edition(edition_id: int, *, run_id: int | None = None) -> bool:
    settings = get_settings()
    with connect() as db:
        row = db.execute("SELECT * FROM editions WHERE id=?", (edition_id,)).fetchone()
    if not row:
        raise ValueError("Выпуск не найден")
    path = Path(row["path"])
    args = ["-ni", "put"]
    if settings["remarkable_force_overwrite"]:
        args.append("--force")
    args.extend([str(path), str(settings["remarkable_folder"])])
    try:
        result = await run_rmapi(args, timeout=180)
        if not result.success:
            raise RuntimeError(result.output)
        with connect() as db:
            db.execute("UPDATE editions SET status='uploaded', uploaded_at=?, upload_error=NULL WHERE id=?", (utcnow(), edition_id))
        return True
    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        with connect() as db:
            db.execute("UPDATE editions SET status='upload_failed', upload_error=? WHERE id=?", (message[:2000], edition_id))
        add_issue("upload_error", message, url=str(path), run_id=run_id)
        return False


def cleanup_retention() -> int:
    settings = get_settings()
    cutoff = datetime.now(UTC) - timedelta(days=int(settings["retention_days"]))
    deleted = 0
    with connect() as db:
        old = db.execute("SELECT id, path FROM editions WHERE created_at < ?", (cutoff.isoformat(),)).fetchall()
        for edition in old:
            path = Path(edition["path"])
            if path.is_file() and path.parent.resolve() == EDITIONS_DIR.resolve():
                path.unlink(missing_ok=True)
            db.execute("DELETE FROM editions WHERE id=?", (edition["id"],))
            deleted += 1
        db.execute("DELETE FROM issues WHERE resolved_at IS NOT NULL AND resolved_at < ?", (cutoff.isoformat(),))
    return deleted
