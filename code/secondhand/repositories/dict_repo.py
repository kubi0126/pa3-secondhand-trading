"""分类与成色字典仓储。"""

from __future__ import annotations

import sqlite3

from ..domain.models import Category, ItemCondition
from .base import execute, fetch_all, fetch_one


class DictionaryRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    # ---------- 分类 ----------
    def list_categories(self, enabled_only: bool = False) -> list[Category]:
        sql = "SELECT * FROM category"
        if enabled_only:
            sql += " WHERE enabled = 1"
        sql += " ORDER BY sort_order, category_id"
        return [Category.from_row(row) for row in fetch_all(self.connection, sql)]

    def find_category(self, category_id: int) -> Category | None:
        row = fetch_one(
            self.connection, "SELECT * FROM category WHERE category_id = ?", (category_id,)
        )
        return Category.from_row(row) if row else None

    def create_category(self, name: str, sort_order: int = 0) -> int:
        cursor = execute(
            self.connection,
            "INSERT INTO category (name, sort_order, enabled) VALUES (?, ?, 1)",
            (name, sort_order),
        )
        return int(cursor.lastrowid)

    def update_category(self, category_id: int, *, name: str | None = None,
                        sort_order: int | None = None,
                        enabled: bool | None = None) -> None:
        current = self.find_category(category_id)
        if current is None:
            return
        execute(
            self.connection,
            "UPDATE category SET name = ?, sort_order = ?, enabled = ? WHERE category_id = ?",
            (
                name if name is not None else current.name,
                sort_order if sort_order is not None else current.sort_order,
                int(enabled) if enabled is not None else int(current.enabled),
                category_id,
            ),
        )

    # ---------- 成色 ----------
    def list_conditions(self, enabled_only: bool = False) -> list[ItemCondition]:
        sql = "SELECT * FROM item_condition"
        if enabled_only:
            sql += " WHERE enabled = 1"
        sql += " ORDER BY sort_order, condition_id"
        return [ItemCondition.from_row(row) for row in fetch_all(self.connection, sql)]

    def find_condition(self, condition_id: int) -> ItemCondition | None:
        row = fetch_one(
            self.connection,
            "SELECT * FROM item_condition WHERE condition_id = ?",
            (condition_id,),
        )
        return ItemCondition.from_row(row) if row else None

    def create_condition(self, name: str, sort_order: int = 0) -> int:
        cursor = execute(
            self.connection,
            "INSERT INTO item_condition (name, sort_order, enabled) VALUES (?, ?, 1)",
            (name, sort_order),
        )
        return int(cursor.lastrowid)

    def update_condition(self, condition_id: int, *, name: str | None = None,
                         sort_order: int | None = None,
                         enabled: bool | None = None) -> None:
        current = self.find_condition(condition_id)
        if current is None:
            return
        execute(
            self.connection,
            """
            UPDATE item_condition
               SET name = ?, sort_order = ?, enabled = ?
             WHERE condition_id = ?
            """,
            (
                name if name is not None else current.name,
                sort_order if sort_order is not None else current.sort_order,
                int(enabled) if enabled is not None else int(current.enabled),
                condition_id,
            ),
        )
