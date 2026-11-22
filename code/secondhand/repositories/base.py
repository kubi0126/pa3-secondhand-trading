"""仓储层公共函数。"""

from __future__ import annotations

import sqlite3
from typing import Any, Iterable, Sequence


def fetch_one(connection: sqlite3.Connection, sql: str,
              params: Sequence[Any] = ()) -> sqlite3.Row | None:
    return connection.execute(sql, params).fetchone()


def fetch_all(connection: sqlite3.Connection, sql: str,
              params: Sequence[Any] = ()) -> list[sqlite3.Row]:
    return list(connection.execute(sql, params).fetchall())


def execute(connection: sqlite3.Connection, sql: str,
            params: Sequence[Any] = ()) -> sqlite3.Cursor:
    return connection.execute(sql, params)


def placeholders(values: Iterable[Any]) -> str:
    return ", ".join("?" for _ in values)
