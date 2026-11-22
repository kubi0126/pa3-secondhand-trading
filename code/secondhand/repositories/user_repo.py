"""用户仓储。"""

from __future__ import annotations

import sqlite3

from ..domain.models import User
from ..utils import fmt, now
from .base import execute, fetch_all, fetch_one


class UserRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def find_by_id(self, user_id: int) -> User | None:
        row = fetch_one(self.connection, "SELECT * FROM user WHERE user_id = ?", (user_id,))
        return User.from_row(row) if row else None

    def find_by_username(self, username: str) -> User | None:
        row = fetch_one(self.connection, "SELECT * FROM user WHERE username = ?", (username,))
        return User.from_row(row) if row else None

    def find_by_login(self, login: str) -> User | None:
        row = fetch_one(
            self.connection,
            "SELECT * FROM user WHERE username = ? OR phone = ?",
            (login, login),
        )
        return User.from_row(row) if row else None

    def exists_username(self, username: str) -> bool:
        return fetch_one(
            self.connection, "SELECT 1 FROM user WHERE username = ?", (username,)
        ) is not None

    def exists_phone(self, phone: str) -> bool:
        return fetch_one(
            self.connection, "SELECT 1 FROM user WHERE phone = ?", (phone,)
        ) is not None

    def insert(self, username: str, phone: str, password_hash: str,
               nickname: str | None, role: str = "USER") -> int:
        timestamp = fmt(now())
        cursor = execute(
            self.connection,
            """
            INSERT INTO user (username, phone, password_hash, nickname, role,
                              created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (username, phone, password_hash, nickname, role, timestamp, timestamp),
        )
        return int(cursor.lastrowid)

    def record_failed_login(self, user_id: int, attempts: int,
                            locked_until: str | None) -> None:
        execute(
            self.connection,
            """
            UPDATE user
               SET failed_attempts = ?, locked_until = ?, updated_at = ?
             WHERE user_id = ?
            """,
            (attempts, locked_until, fmt(now()), user_id),
        )

    def reset_failed_login(self, user_id: int) -> None:
        execute(
            self.connection,
            """
            UPDATE user
               SET failed_attempts = 0, locked_until = NULL, updated_at = ?
             WHERE user_id = ?
            """,
            (fmt(now()), user_id),
        )

    def list_all(self) -> list[User]:
        rows = fetch_all(self.connection, "SELECT * FROM user ORDER BY user_id")
        return [User.from_row(row) for row in rows]
