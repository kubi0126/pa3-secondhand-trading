"""浏览与查询服务（REQ-007/015）。"""

from __future__ import annotations

import sqlite3
from typing import Any

from ..domain.errors import ValidationError
from ..repositories.dict_repo import DictionaryRepository
from ..repositories.item_repo import ItemFilters, ItemRepository
from ..utils import Page, parse_page


class QueryService:
    def __init__(self, connection: sqlite3.Connection, *, default_page_size: int = 20,
                 max_page_size: int = 100) -> None:
        self.connection = connection
        self.default_page_size = default_page_size
        self.max_page_size = max_page_size

    def _price(self, raw: Any, field: str) -> float | None:
        if raw is None or str(raw).strip() == "":
            return None
        try:
            value = float(raw)
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"{field}必须是数字") from exc
        if value < 0:
            raise ValidationError(f"{field}不能为负数")
        return value

    def browse(self, args: dict[str, Any]) -> dict[str, Any]:
        keyword = str(args.get("q") or "").strip()[:60]
        category_raw = str(args.get("category") or "").strip()
        try:
            category_id = int(category_raw) if category_raw else None
        except ValueError as exc:
            raise ValidationError("分类参数不正确") from exc

        min_price = self._price(args.get("min_price"), "最低价")
        max_price = self._price(args.get("max_price"), "最高价")
        if min_price is not None and max_price is not None and min_price > max_price:
            raise ValidationError("最低价不能大于最高价")

        sort = str(args.get("sort") or "newest")
        if sort not in {"newest", "price_asc", "price_desc"}:
            raise ValidationError("排序参数不正确")

        page = parse_page(
            args.get("page"), args.get("page_size"),
            default_size=self.default_page_size,
            max_size=self.max_page_size,
        )
        filters = ItemFilters(
            keyword=keyword,
            category_id=category_id,
            min_price=min_price,
            max_price=max_price,
            sort=sort,
        )
        repo = ItemRepository(self.connection)
        page.total = repo.count_browse(filters)
        items = repo.browse(filters, page.page_size, page.offset)
        categories = DictionaryRepository(self.connection).list_categories(enabled_only=True)
        return {
            "items": items,
            "page": page,
            "categories": categories,
            "filters": {
                "q": keyword,
                "category": category_id,
                "min_price": min_price,
                "max_price": max_price,
                "sort": sort,
            },
        }
