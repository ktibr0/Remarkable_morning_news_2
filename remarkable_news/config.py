from __future__ import annotations

import os
from pathlib import Path


DATA_DIR = Path(os.getenv("APP_DATA_DIR", "./data")).resolve()
DB_PATH = DATA_DIR / "news.db"
EDITIONS_DIR = DATA_DIR / "editions"
IMAGES_DIR = DATA_DIR / "images"
LOGS_DIR = DATA_DIR / "logs"
GOTENBERG_URL = os.getenv("GOTENBERG_URL", "http://gotenberg:3000").rstrip("/")
RMAPI_CONFIG = Path(os.getenv("RMAPI_CONFIG", str(DATA_DIR / "rmapi.conf")))
TIMEZONE = os.getenv("APP_TIMEZONE", "Europe/Moscow")


DEFAULT_SETTINGS: dict[str, object] = {
    "schedule_enabled": True,
    "schedule_interval_minutes": 360,
    "max_items_per_feed": 25,
    "article_lookback_hours": 48,
    "request_timeout_seconds": 25,
    "minimum_content_chars": 300,
    "prefer_full_article": True,
    "include_images": True,
    "max_image_bytes": 3_000_000,
    "max_articles_per_edition": 50,
    "retry_attempts": 5,
    "retry_base_minutes": 15,
    "retention_days": 30,
    "create_empty_editions": False,
    "remarkable_enabled": False,
    "remarkable_folder": "/News",
    "remarkable_force_overwrite": False,
    "edition_title": "Morning News",
    "paper_size": "A4",
    "font_size_pt": 12,
    "line_height": 1.45,
    "page_margin_mm": 16,
    "article_page_break": False,
    "show_source": True,
    "show_date": True,
    "show_links": True,
}


def ensure_directories() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    EDITIONS_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    RMAPI_CONFIG.parent.mkdir(parents=True, exist_ok=True)
