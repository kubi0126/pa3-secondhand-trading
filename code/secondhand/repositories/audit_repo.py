"""审核记录仓储（只增不改）。"""

from __future__ import annotations

import sqlite3

from ..domain.models import AuditRecord
from ..utils import fmt, now
from .base import execute, fetch_all, fetch_one


class AuditRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def insert(self, item_id: int, admin_id: int, result: str,
               reason: str | None) -> int:
        cursor = execute(
            self.connection,
            """
            INSERT INTO audit_record (item_id, admin_id, result, reason, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (item_id, admin_id, result, reason, fmt(now())),
        )
        return int(cursor.lastrowid)

    def list_by_item(self, item_id: int) -> list[AuditRecord]:
        rows = fetch_all(
            self.connection,
            """
            SELECT a.*,
                   COALESCE(u.nickname, u.username) AS admin_name,
                   i.title AS item_title
              FROM audit_record a
              JOIN user u ON u.user_id = a.admin_id
              JOIN item i ON i.item_id = a.item_id
             WHERE a.item_id = ?
             ORDER BY a.created_at DESC, a.audit_id DESC
            """,
            (item_id,),
        )
        return [AuditRecord.from_row(row) for row in rows]

    def latest_for_item(self, item_id: int) -> AuditRecord | None:
        row = fetch_one(
            self.connection,
            """
            SELECT a.*,
                   COALESCE(u.nickname, u.username) AS admin_name,
                   i.title AS item_title
              FROM audit_record a
              JOIN user u ON u.user_id = a.admin_id
              JOIN item i ON i.item_id = a.item_id
             WHERE a.item_id = ?
             ORDER BY a.created_at DESC, a.audit_id DESC
             LIMIT 1
            """,
            (item_id,),
        )
        return AuditRecord.from_row(row) if row else None
