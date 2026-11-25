"""预约仓储：唯一有效预约、状态更新与超时扫描。"""

from __future__ import annotations

import sqlite3
from typing import Any

from ..domain.models import Reservation
from ..utils import fmt, now
from .base import execute, fetch_all, fetch_one

RESERVATION_SELECT = """
SELECT r.*,
       i.title AS item_title,
       i.price AS item_price,
       i.status AS item_status,
       i.seller_id AS seller_id,
       COALESCE(b.nickname, b.username) AS buyer_name,
       COALESCE(s.nickname, s.username) AS seller_name
  FROM reservation r
  JOIN item i ON i.item_id = r.item_id
  JOIN user b ON b.user_id = r.buyer_id
  JOIN user s ON s.user_id = i.seller_id
"""


class ReservationRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def find_by_id(self, reservation_id: int) -> Reservation | None:
        row = fetch_one(
            self.connection,
            RESERVATION_SELECT + " WHERE r.reservation_id = ?",
            (reservation_id,),
        )
        return Reservation.from_row(row) if row else None

    def insert(self, item_id: int, buyer_id: int, request_id: str,
               expire_at: str) -> int:
        cursor = execute(
            self.connection,
            """
            INSERT INTO reservation (item_id, buyer_id, status, version, request_id,
                                     created_at, expire_at)
            VALUES (?, ?, 'PENDING_CONFIRM', 0, ?, ?, ?)
            """,
            (item_id, buyer_id, request_id, fmt(now()), expire_at),
        )
        return int(cursor.lastrowid)

    def find_active_by_item(self, item_id: int) -> Reservation | None:
        row = fetch_one(
            self.connection,
            RESERVATION_SELECT
            + """
              WHERE r.item_id = ? AND r.status IN ('PENDING_CONFIRM', 'CONFIRMED')
              ORDER BY r.reservation_id DESC
              LIMIT 1
            """,
            (item_id,),
        )
        return Reservation.from_row(row) if row else None

    def find_active_by_buyer_item(self, buyer_id: int, item_id: int) -> Reservation | None:
        row = fetch_one(
            self.connection,
            RESERVATION_SELECT
            + """
              WHERE r.buyer_id = ? AND r.item_id = ?
                AND r.status IN ('PENDING_CONFIRM', 'CONFIRMED')
              LIMIT 1
            """,
            (buyer_id, item_id),
        )
        return Reservation.from_row(row) if row else None

    def find_recent_by_buyer_item(self, buyer_id: int, item_id: int,
                                  since: str) -> Reservation | None:
        """60 秒内仍有效的预约；已取消/已拒绝/已完成不算重复。"""
        row = fetch_one(
            self.connection,
            RESERVATION_SELECT
            + """
              WHERE r.buyer_id = ? AND r.item_id = ? AND r.created_at >= ?
                AND r.status IN ('PENDING_CONFIRM', 'CONFIRMED')
              ORDER BY r.created_at DESC
              LIMIT 1
            """,
            (buyer_id, item_id, since),
        )
        return Reservation.from_row(row) if row else None

    def change_status(self, reservation_id: int, from_status: str, to_status: str,
                      expected_version: int | None = None,
                      *, cancel_reason: str | None = None,
                      confirmed_at: str | None = None,
                      completed_at: str | None = None,
                      expire_at: str | None = None) -> int:
        sql = """
            UPDATE reservation
               SET status = ?, version = version + 1,
                   cancel_reason = COALESCE(?, cancel_reason),
                   confirmed_at = COALESCE(?, confirmed_at),
                   completed_at = COALESCE(?, completed_at),
                   expire_at = COALESCE(?, expire_at)
             WHERE reservation_id = ? AND status = ?
        """
        params: list[Any] = [
            to_status, cancel_reason, confirmed_at, completed_at, expire_at,
            reservation_id, from_status,
        ]
        if expected_version is not None:
            sql += " AND version = ?"
            params.append(expected_version)
        return execute(self.connection, sql, params).rowcount

    def _list_where(self, buyer_id: int, status: str | None) -> tuple[str, list[Any]]:
        clauses = ["r.buyer_id = ?"]
        params: list[Any] = [buyer_id]
        if status:
            clauses.append("r.status = ?")
            params.append(status)
        return " WHERE " + " AND ".join(clauses), params

    def list_by_buyer(self, buyer_id: int, status: str | None,
                      limit: int, offset: int) -> list[Reservation]:
        where, params = self._list_where(buyer_id, status)
        sql = (
            RESERVATION_SELECT + where
            + " ORDER BY r.created_at DESC, r.reservation_id DESC LIMIT ? OFFSET ?"
        )
        rows = fetch_all(self.connection, sql, [*params, limit, offset])
        return [Reservation.from_row(row) for row in rows]

    def count_by_buyer(self, buyer_id: int, status: str | None) -> int:
        where, params = self._list_where(buyer_id, status)
        row = fetch_one(
            self.connection, "SELECT COUNT(*) AS total FROM reservation r" + where, params
        )
        return int(row["total"]) if row else 0

    def list_pending_by_seller(self, seller_id: int, limit: int,
                               offset: int) -> list[Reservation]:
        sql = RESERVATION_SELECT + """
             WHERE i.seller_id = ? AND r.status = 'PENDING_CONFIRM'
             ORDER BY r.created_at ASC, r.reservation_id ASC
             LIMIT ? OFFSET ?
        """
        rows = fetch_all(self.connection, sql, [seller_id, limit, offset])
        return [Reservation.from_row(row) for row in rows]

    def count_pending_by_seller(self, seller_id: int) -> int:
        row = fetch_one(
            self.connection,
            """
            SELECT COUNT(*) AS total
              FROM reservation r
              JOIN item i ON i.item_id = r.item_id
             WHERE i.seller_id = ? AND r.status = 'PENDING_CONFIRM'
            """,
            (seller_id,),
        )
        return int(row["total"]) if row else 0

    def list_by_seller(self, seller_id: int, status: str | None,
                       limit: int, offset: int) -> list[Reservation]:
        sql = RESERVATION_SELECT + " WHERE i.seller_id = ?"
        params: list[Any] = [seller_id]
        if status:
            sql += " AND r.status = ?"
            params.append(status)
        sql += " ORDER BY r.created_at DESC, r.reservation_id DESC LIMIT ? OFFSET ?"
        rows = fetch_all(self.connection, sql, [*params, limit, offset])
        return [Reservation.from_row(row) for row in rows]

    def count_by_seller(self, seller_id: int, status: str | None) -> int:
        sql = """
            SELECT COUNT(*) AS total
              FROM reservation r
              JOIN item i ON i.item_id = r.item_id
             WHERE i.seller_id = ?
        """
        params: list[Any] = [seller_id]
        if status:
            sql += " AND r.status = ?"
            params.append(status)
        row = fetch_one(self.connection, sql, params)
        return int(row["total"]) if row else 0

    def list_due(self, current: str, limit: int = 100) -> list[Reservation]:
        sql = RESERVATION_SELECT + """
             WHERE r.status IN ('PENDING_CONFIRM', 'CONFIRMED')
               AND r.expire_at <= ?
             ORDER BY r.expire_at ASC
             LIMIT ?
        """
        rows = fetch_all(self.connection, sql, (current, limit))
        return [Reservation.from_row(row) for row in rows]

    def count_active_by_seller(self, seller_id: int) -> int:
        row = fetch_one(
            self.connection,
            """
            SELECT COUNT(*) AS total
              FROM reservation r
              JOIN item i ON i.item_id = r.item_id
             WHERE i.seller_id = ?
               AND r.status IN ('PENDING_CONFIRM', 'CONFIRMED')
            """,
            (seller_id,),
        )
        return int(row["total"]) if row else 0

    def count_active(self) -> int:
        row = fetch_one(
            self.connection,
            "SELECT COUNT(*) AS total FROM reservation "
            "WHERE status IN ('PENDING_CONFIRM', 'CONFIRMED')",
        )
        return int(row["total"]) if row else 0
