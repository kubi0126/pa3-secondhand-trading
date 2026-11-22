"""商品仓储：列表查询、状态更新与乐观锁。"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any

from ..domain.models import Item
from ..utils import fmt, now
from .base import execute, fetch_all, fetch_one

ITEM_SELECT = """
SELECT i.*,
       c.name AS category_name,
       k.name AS condition_name,
       COALESCE(u.nickname, u.username) AS seller_name
  FROM item i
  JOIN category c ON c.category_id = i.category_id
  JOIN item_condition k ON k.condition_id = i.condition_id
  JOIN user u ON u.user_id = i.seller_id
"""


@dataclass
class ItemFilters:
    keyword: str = ""
    category_id: int | None = None
    min_price: float | None = None
    max_price: float | None = None
    status: str | None = None
    sort: str = "newest"


class ItemRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    # ---------- 单条 ----------
    def find_by_id(self, item_id: int) -> Item | None:
        row = fetch_one(self.connection, ITEM_SELECT + " WHERE i.item_id = ?", (item_id,))
        return Item.from_row(row) if row else None

    def insert(self, seller_id: int, category_id: int, condition_id: int,
               title: str, description: str | None, price: float,
               image_url: str | None) -> int:
        timestamp = fmt(now())
        cursor = execute(
            self.connection,
            """
            INSERT INTO item (seller_id, category_id, condition_id, title, description,
                              price, image_url, status, version, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'DRAFT', 0, ?, ?)
            """,
            (seller_id, category_id, condition_id, title, description,
             price, image_url, timestamp, timestamp),
        )
        return int(cursor.lastrowid)

    def update_content(self, item_id: int, *, title: str, description: str | None,
                       category_id: int, condition_id: int, price: float,
                       image_url: str | None, status: str,
                       expected_version: int) -> int:
        """更新商品内容并把版本号 +1；返回影响行数（0 表示版本冲突）。"""

        cursor = execute(
            self.connection,
            """
            UPDATE item
               SET title = ?, description = ?, category_id = ?, condition_id = ?,
                   price = ?, image_url = ?, status = ?, version = version + 1,
                   updated_at = ?
             WHERE item_id = ? AND version = ?
            """,
            (title, description, category_id, condition_id, price, image_url,
             status, fmt(now()), item_id, expected_version),
        )
        return cursor.rowcount

    def change_status(self, item_id: int, from_status: str, to_status: str,
                      expected_version: int | None = None,
                      published_at: str | None = None) -> int:
        sql = """
            UPDATE item
               SET status = ?, version = version + 1,
                   published_at = COALESCE(?, published_at),
                   updated_at = ?
             WHERE item_id = ? AND status = ?
        """
        params: list[Any] = [to_status, published_at, fmt(now()), item_id, from_status]
        if expected_version is not None:
            sql += " AND version = ?"
            params.append(expected_version)
        return execute(self.connection, sql, params).rowcount

    # ---------- 买家浏览 ----------
    def _browse_where(self, filters: ItemFilters) -> tuple[str, list[Any]]:
        clauses = ["i.status = 'PUBLISHED'"]
        params: list[Any] = []
        if filters.keyword:
            clauses.append("(i.title LIKE ? OR i.description LIKE ?)")
            like = f"%{filters.keyword}%"
            params.extend([like, like])
        if filters.category_id:
            clauses.append("i.category_id = ?")
            params.append(filters.category_id)
        if filters.min_price is not None:
            clauses.append("i.price >= ?")
            params.append(filters.min_price)
        if filters.max_price is not None:
            clauses.append("i.price <= ?")
            params.append(filters.max_price)
        return " WHERE " + " AND ".join(clauses), params

    def _order_by(self, sort: str) -> str:
        return {
            "newest": " ORDER BY i.published_at DESC, i.item_id DESC",
            "price_asc": " ORDER BY i.price ASC, i.item_id DESC",
            "price_desc": " ORDER BY i.price DESC, i.item_id DESC",
        }.get(sort, " ORDER BY i.published_at DESC, i.item_id DESC")

    def browse(self, filters: ItemFilters, limit: int, offset: int) -> list[Item]:
        where, params = self._browse_where(filters)
        sql = ITEM_SELECT + where + self._order_by(filters.sort) + " LIMIT ? OFFSET ?"
        rows = fetch_all(self.connection, sql, [*params, limit, offset])
        return [Item.from_row(row) for row in rows]

    def count_browse(self, filters: ItemFilters) -> int:
        where, params = self._browse_where(filters)
        row = fetch_one(self.connection, "SELECT COUNT(*) AS total FROM item i" + where, params)
        return int(row["total"]) if row else 0

    # ---------- 卖家 / 管理员 ----------
    def list_by_seller(self, seller_id: int, status: str | None,
                       limit: int, offset: int) -> list[Item]:
        sql = ITEM_SELECT + " WHERE i.seller_id = ?"
        params: list[Any] = [seller_id]
        if status:
            sql += " AND i.status = ?"
            params.append(status)
        sql += " ORDER BY i.updated_at DESC, i.item_id DESC LIMIT ? OFFSET ?"
        rows = fetch_all(self.connection, sql, [*params, limit, offset])
        return [Item.from_row(row) for row in rows]

    def count_by_seller(self, seller_id: int, status: str | None) -> int:
        sql = "SELECT COUNT(*) AS total FROM item WHERE seller_id = ?"
        params: list[Any] = [seller_id]
        if status:
            sql += " AND status = ?"
            params.append(status)
        row = fetch_one(self.connection, sql, params)
        return int(row["total"]) if row else 0

    def list_for_admin(self, status: str | None, keyword: str,
                       limit: int, offset: int) -> list[Item]:
        sql = ITEM_SELECT + " WHERE i.status <> 'DRAFT'"
        params: list[Any] = []
        if status:
            sql += " AND i.status = ?"
            params.append(status)
        if keyword:
            sql += " AND i.title LIKE ?"
            params.append(f"%{keyword}%")
        sql += " ORDER BY i.updated_at DESC, i.item_id DESC LIMIT ? OFFSET ?"
        rows = fetch_all(self.connection, sql, [*params, limit, offset])
        return [Item.from_row(row) for row in rows]

    def count_for_admin(self, status: str | None, keyword: str) -> int:
        sql = "SELECT COUNT(*) AS total FROM item WHERE status <> 'DRAFT'"
        params: list[Any] = []
        if status:
            sql += " AND status = ?"
            params.append(status)
        if keyword:
            sql += " AND title LIKE ?"
            params.append(f"%{keyword}%")
        row = fetch_one(self.connection, sql, params)
        return int(row["total"]) if row else 0

    def list_pending_review(self, limit: int, offset: int) -> list[Item]:
        sql = ITEM_SELECT + """
             WHERE i.status = 'PENDING_REVIEW'
             ORDER BY i.updated_at ASC, i.item_id ASC
             LIMIT ? OFFSET ?
        """
        rows = fetch_all(self.connection, sql, [limit, offset])
        return [Item.from_row(row) for row in rows]

    def count_pending_review(self) -> int:
        row = fetch_one(
            self.connection, "SELECT COUNT(*) AS total FROM item WHERE status = 'PENDING_REVIEW'"
        )
        return int(row["total"]) if row else 0

    def count_by_status_for_seller(self, seller_id: int) -> dict[str, int]:
        rows = fetch_all(
            self.connection,
            "SELECT status, COUNT(*) AS total FROM item WHERE seller_id = ? GROUP BY status",
            (seller_id,),
        )
        return {row["status"]: int(row["total"]) for row in rows}

    def count_by_category(self) -> list[dict[str, Any]]:
        rows = fetch_all(
            self.connection,
            """
            SELECT c.category_id, c.name,
                   SUM(CASE WHEN i.status = 'PUBLISHED' THEN 1 ELSE 0 END) AS published,
                   SUM(CASE WHEN i.status = 'RESERVED' THEN 1 ELSE 0 END) AS reserved,
                   SUM(CASE WHEN i.status = 'SOLD' THEN 1 ELSE 0 END) AS sold,
                   COUNT(i.item_id) AS total
              FROM category c
              LEFT JOIN item i ON i.category_id = c.category_id
             GROUP BY c.category_id, c.name
             ORDER BY c.sort_order, c.category_id
            """,
        )
        return [dict(row) for row in rows]
