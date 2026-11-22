"""商品服务：草稿、编辑、提交审核、下架与详情可见性。"""

from __future__ import annotations

import sqlite3
from typing import Any

from ..db import transaction
from ..domain.enums import ItemStatus, Role
from ..domain.errors import NotFound, PermissionDenied, StateConflict, ValidationError
from ..domain.models import Item, User
from ..domain.state_machines import assert_item_transition
from ..repositories.audit_repo import AuditRepository
from ..repositories.dict_repo import DictionaryRepository
from ..repositories.item_repo import ItemRepository
from ..repositories.log_repo import LogAction, LogRepository
from ..repositories.reservation_repo import ReservationRepository
from ..utils import Page, URL_PATTERN, money, text
from .dto import ItemInput


class ItemService:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    # ---------- 校验 ----------
    def _validate(self, data: ItemInput) -> dict[str, Any]:
        title = text(data.title, "标题", max_len=60)
        description = text(data.description, "描述", required=False, max_len=2000)
        price = money(data.price)
        image_url = text(data.image_url, "图片链接", required=False, max_len=512)
        if image_url and not URL_PATTERN.match(image_url):
            raise ValidationError("图片链接必须以 http:// 或 https:// 开头")

        dict_repo = DictionaryRepository(self.connection)
        category = dict_repo.find_category(int(data.category_id))
        if category is None or not category.enabled:
            raise ValidationError("分类不存在或已停用")
        condition = dict_repo.find_condition(int(data.condition_id))
        if condition is None or not condition.enabled:
            raise ValidationError("成色不存在或已停用")

        return {
            "title": title,
            "description": description or None,
            "category_id": category.category_id,
            "condition_id": condition.condition_id,
            "price": price,
            "image_url": image_url or None,
        }

    @staticmethod
    def _require_seller(item: Item, seller_id: int) -> None:
        if item.seller_id != seller_id:
            raise PermissionDenied("只能操作自己发布的商品")

    # ---------- 写操作 ----------
    def create_draft(self, seller_id: int, data: ItemInput) -> int:
        values = self._validate(data)
        with transaction() as connection:
            item_repo = ItemRepository(connection)
            item_id = item_repo.insert(
                seller_id=seller_id,
                category_id=values["category_id"],
                condition_id=values["condition_id"],
                title=values["title"],
                description=values["description"],
                price=values["price"],
                image_url=values["image_url"],
            )
            LogRepository(connection).insert(
                operator_id=seller_id,
                operator_type="USER",
                target_type="ITEM",
                target_id=item_id,
                action=LogAction.ITEM_CREATE,
                detail=f"创建草稿：{values['title']}",
            )
            return item_id

    def update(self, seller_id: int, item_id: int, data: ItemInput,
               expected_version: int) -> ItemStatus:
        item = ItemRepository(self.connection).find_by_id(item_id)
        if item is None:
            raise NotFound("商品不存在")
        self._require_seller(item, seller_id)
        if item.status not in {ItemStatus.DRAFT, ItemStatus.REJECTED, ItemStatus.PUBLISHED}:
            raise StateConflict(f"商品当前为“{item.status.label}”，不能编辑")

        values = self._validate(data)
        key_changed = (
            values["title"] != item.title
            or abs(values["price"] - item.price) > 0.001
            or values["category_id"] != item.category_id
        )
        target_status = item.status
        if item.status is ItemStatus.PUBLISHED and key_changed:
            target_status = ItemStatus.PENDING_REVIEW
            assert_item_transition(item.status, target_status)

        with transaction() as connection:
            changed = ItemRepository(connection).update_content(
                item_id,
                title=values["title"],
                description=values["description"],
                category_id=values["category_id"],
                condition_id=values["condition_id"],
                price=values["price"],
                image_url=values["image_url"],
                status=target_status.value,
                expected_version=expected_version,
            )
            if changed == 0:
                raise StateConflict("数据已变化，请刷新后重试")
            LogRepository(connection).insert(
                operator_id=seller_id,
                operator_type="USER",
                target_type="ITEM",
                target_id=item_id,
                action=LogAction.ITEM_UPDATE,
                detail=f"修改商品，状态 {item.status.value} → {target_status.value}",
            )
            return target_status

    def submit(self, seller_id: int, item_id: int, expected_version: int) -> None:
        item = ItemRepository(self.connection).find_by_id(item_id)
        if item is None:
            raise NotFound("商品不存在")
        self._require_seller(item, seller_id)
        if item.status not in {ItemStatus.DRAFT, ItemStatus.REJECTED, ItemStatus.PUBLISHED}:
            raise StateConflict(f"商品当前为“{item.status.label}”，不能提交审核")
        if not item.title.strip() or item.price <= 0:
            raise ValidationError("商品信息不完整，不能提交审核")
        assert_item_transition(item.status, ItemStatus.PENDING_REVIEW)

        with transaction() as connection:
            changed = ItemRepository(connection).change_status(
                item_id, item.status.value, ItemStatus.PENDING_REVIEW.value,
                expected_version=expected_version,
            )
            if changed == 0:
                raise StateConflict("数据已变化，请刷新后重试")
            LogRepository(connection).insert(
                operator_id=seller_id,
                operator_type="USER",
                target_type="ITEM",
                target_id=item_id,
                action=LogAction.ITEM_SUBMIT,
                detail="提交审核",
            )

    def delist(self, seller_id: int, item_id: int, expected_version: int) -> None:
        item = ItemRepository(self.connection).find_by_id(item_id)
        if item is None:
            raise NotFound("商品不存在")
        self._require_seller(item, seller_id)
        if item.status is not ItemStatus.PUBLISHED:
            raise StateConflict(f"商品当前为“{item.status.label}”，不能下架")
        active = ReservationRepository(self.connection).find_active_by_item(item_id)
        if active is not None:
            raise StateConflict("商品存在有效预约，请先处理预约")
        assert_item_transition(item.status, ItemStatus.DELISTED)

        with transaction() as connection:
            changed = ItemRepository(connection).change_status(
                item_id, item.status.value, ItemStatus.DELISTED.value,
                expected_version=expected_version,
            )
            if changed == 0:
                raise StateConflict("数据已变化，请刷新后重试")
            LogRepository(connection).insert(
                operator_id=seller_id,
                operator_type="USER",
                target_type="ITEM",
                target_id=item_id,
                action=LogAction.ITEM_DELIST,
                detail="卖家下架",
            )

    # ---------- 查询 ----------
    def get_detail(self, item_id: int, viewer: User | None) -> dict[str, Any]:
        item = ItemRepository(self.connection).find_by_id(item_id)
        if item is None:
            raise NotFound("商品不存在")
        self._assert_visible(item, viewer)
        audit_repo = AuditRepository(self.connection)
        reservation_repo = ReservationRepository(self.connection)
        return {
            "item": item,
            "audits": audit_repo.list_by_item(item_id),
            "active_reservation": reservation_repo.find_active_by_item(item_id),
        }

    @staticmethod
    def _assert_visible(item: Item, viewer: User | None) -> None:
        if item.status in {ItemStatus.PUBLISHED, ItemStatus.RESERVED}:
            return
        if item.status is ItemStatus.SOLD:
            if viewer is None:
                raise PermissionDenied("已售出商品详情需登录后查看")
            return
        if viewer is None:
            raise PermissionDenied("该商品详情仅卖家本人和管理员可见")
        if viewer.role is Role.ADMIN or viewer.user_id == item.seller_id:
            return
        raise PermissionDenied("该商品详情仅卖家本人和管理员可见")

    def list_my(self, seller_id: int, status: str | None,
                page: Page) -> list[Item]:
        repo = ItemRepository(self.connection)
        page.total = repo.count_by_seller(seller_id, status)
        return repo.list_by_seller(seller_id, status, page.page_size, page.offset)

    def seller_stats(self, seller_id: int) -> dict[str, int]:
        repo = ItemRepository(self.connection)
        counts = repo.count_by_status_for_seller(seller_id)
        reservation_repo = ReservationRepository(self.connection)
        return {
            "published": counts.get("PUBLISHED", 0),
            "reserved": counts.get("RESERVED", 0),
            "sold": counts.get("SOLD", 0),
            "draft": counts.get("DRAFT", 0),
            "pending_review": counts.get("PENDING_REVIEW", 0),
            "rejected": counts.get("REJECTED", 0),
            "active_reservations": reservation_repo.count_active_by_seller(seller_id),
        }
