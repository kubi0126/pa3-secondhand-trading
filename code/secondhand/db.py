"""SQLite 连接、事务与 Flask 生命周期集成。"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from flask import current_app, g

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


class Database:
    """封装 SQLite 连接。

    设计要点：
    - isolation_level=None：由 transaction() 显式控制 BEGIN/COMMIT；
    - BEGIN IMMEDIATE：写事务一开始就取写锁，避免并发预约时的竞态；
    - WAL + busy_timeout：读写并发时减少 database is locked。
    """

    def __init__(self, path: str) -> None:
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path,
            timeout=15,
            isolation_level=None,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def init_schema(self) -> None:
        connection = self.connect()
        try:
            connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        finally:
            connection.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()


def init_app(app) -> None:
    """把 Database 挂到 app.extensions，并注册请求级连接。"""

    app.extensions["db"] = Database(app.config["DATABASE"])

    def _get_db() -> sqlite3.Connection:
        if "db" not in g:
            g.db = app.extensions["db"].connect()
        return g.db

    def close_db(_exception: BaseException | None = None) -> None:
        connection = g.pop("db", None)
        if connection is not None:
            connection.close()

    app.get_db = _get_db  # type: ignore[attr-defined]
    app.teardown_appcontext(close_db)


def get_db() -> sqlite3.Connection:
    """请求内复用同一个连接。"""

    return current_app.get_db()  # type: ignore[attr-defined]


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    """在请求连接上开启写事务。"""

    connection = get_db()
    try:
        connection.execute("BEGIN IMMEDIATE")
        yield connection
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise
