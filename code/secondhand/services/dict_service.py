"""分类与成色字典服务（REQ-003/014）。"""

from __future__ import annotations

import sqlite3

from ..domain.errors import StateConflict, ValidationError
from ..repositories.dict_repo import DictionaryRepository
from ..utils import text


class DictService:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list_all(self) -> dict[str, list]:
        repo = DictionaryRepository(self.connection)
        return {
            "categories": repo.list_categories(),
            "conditions": repo.list_conditions(),
        }

    def create_category(self, name: str, sort_order: int = 0) -> int:
        cleaned = text(name, "分类名称", max_len=32)
        try:
            return DictionaryRepository(self.connection).create_category(cleaned, sort_order)
        except sqlite3.IntegrityError as exc:
            raise StateConflict("分类名称已存在") from exc

    def create_condition(self, name: str, sort_order: int = 0) -> int:
        cleaned = text(name, "成色名称", max_len=16)
        try:
            return DictionaryRepository(self.connection).create_condition(cleaned, sort_order)
        except sqlite3.IntegrityError as exc:
            raise StateConflict("成色名称已存在") from exc

    def toggle_category(self, category_id: int) -> None:
        repo = DictionaryRepository(self.connection)
        category = repo.find_category(category_id)
        if category is None:
            raise ValidationError("分类不存在")
        repo.update_category(category_id, enabled=not category.enabled)

    def toggle_condition(self, condition_id: int) -> None:
        repo = DictionaryRepository(self.connection)
        condition = repo.find_condition(condition_id)
        if condition is None:
            raise ValidationError("成色不存在")
        repo.update_condition(condition_id, enabled=not condition.enabled)
