"""幂等请求表仓储。"""

from __future__ import annotations

import sqlite3

from ..domain.models import RequestLog
from ..utils import fmt, now
from .base import execute, fetch_one


class RequestRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def find(self, request_id: str) -> RequestLog | None:
        row = fetch_one(
            self.connection, "SELECT * FROM request_log WHERE request_id = ?", (request_id,)
        )
        return RequestLog.from_row(row) if row else None

    def try_start(self, request_id: str, user_id: int, endpoint: str) -> bool:
        """原子占位；已存在返回 False。"""

        cursor = execute(
            self.connection,
            """
            INSERT INTO request_log (request_id, user_id, endpoint, status,
                                     created_at, updated_at)
            VALUES (?, ?, ?, 'PROCESSING', ?, ?)
            ON CONFLICT (request_id) DO NOTHING
            """,
            (request_id, user_id, endpoint, fmt(now()), fmt(now())),
        )
        return cursor.rowcount == 1

    def mark_success(self, request_id: str, result_json: str) -> None:
        execute(
            self.connection,
            """
            UPDATE request_log
               SET status = 'SUCCESS', result_json = ?, updated_at = ?
             WHERE request_id = ?
            """,
            (result_json, fmt(now()), request_id),
        )

    def mark_failed(self, request_id: str, result_json: str | None = None) -> None:
        execute(
            self.connection,
            """
            UPDATE request_log
               SET status = 'FAILED', result_json = ?, updated_at = ?
             WHERE request_id = ?
            """,
            (result_json, fmt(now()), request_id),
        )

    def restart(self, request_id: str) -> None:
        """FAILED 的请求允许用同一个 request_id 重试。"""

        execute(
            self.connection,
            """
            UPDATE request_log
               SET status = 'PROCESSING', result_json = NULL, updated_at = ?
             WHERE request_id = ? AND status = 'FAILED'
            """,
            (fmt(now()), request_id),
        )

    def cleanup(self, before: str) -> int:
        cursor = execute(
            self.connection, "DELETE FROM request_log WHERE created_at < ?", (before,)
        )
        return cursor.rowcount
