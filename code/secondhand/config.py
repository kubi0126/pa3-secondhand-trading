"""应用配置。"""

from __future__ import annotations

import os
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB = CODE_DIR / "var" / "secondhand.db"


class Config:
    """默认配置，测试时可通过 create_app(config) 覆盖。"""

    SECRET_KEY = os.environ.get("SECONDHAND_SECRET", "dev-secret-please-change")
    DATABASE = os.environ.get("SECONDHAND_DB", str(DEFAULT_DB))
    TESTING = False
    CSRF_ENABLED = True

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024

    PER_PAGE = 20
    MAX_PAGE_SIZE = 100

    LOGIN_MAX_ATTEMPTS = 5
    LOGIN_LOCK_MINUTES = 15

    RESERVATION_CONFIRM_HOURS = 24
    RESERVATION_COMPLETE_HOURS = 48
    DUPLICATE_RESERVATION_SECONDS = 60
    REQUEST_LOG_RETENTION_DAYS = 7
    SCHEDULER_ENABLED = False
    SCHEDULER_INTERVAL_SECONDS = 60
    SEED_DATA = True
