"""审核与违规处置服务（REQ-005/020）。"""

from __future__ import annotations

import sqlite3

from ..db import transaction
from ..domain.enums import AuditResult, ItemStatus
from ..domain.errors import NotFound, StateConflict
from ..domain.models import Item
from ..domain.state_machines import assert_item_transition
from ..repositories.audit_repo import AuditRepository
from ..repositories.item_repo import ItemRepository
from ..repositories.log_repo import LogAction, LogRepository
from ..repositories.reservation_repo import ReservationRepository
from ..utils import Page, fmt, now, text


class AuditService:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def _pending_item(self, item_id: int) -> Item:
        item = ItemRepository(self.connection).find_by_id(item_id)
        if item is None:
            raise NotFound("商品不存在")
        if item.status is not ItemStatus.PENDING_REVIEW:
            raise StateConflict(f"商品当前为“{item.status.label}”，不能审核")
        return item

    def approve(self, admin_id: int, item_id: int, expected_version: int) -> None:
        item = self._pending_item(item_id)
        assert_item_transition(item.status, ItemStatus.PUBLISHED)
        with transaction() as connection:
            changed = ItemRepository(connection).change_status(
                item_id,
                ItemStatus.PENDING_REVIEW.value,
                ItemStatus.PUBLISHED.value,
                expected_version=expected_version,
                published_at=fmt(now()),
            )
            if changed == 0:
                raise StateConflict("数据已变化，请刷新后重试")
            AuditRepository(connection).insert(
                item_id, admin_id, AuditResult.APPROVED.value, None
            )
            LogRepository(connection).insert(
                operator_id=admin_id,
                operator_type="USER",
                target_type="ITEM",
                target_id=item_id,
                action=LogAction.ITEM_APPROVE,
                detail="审核通过",
            )

    def reject(self, admin_id: int, item_id: int, reason: str,
               expected_version: int) -> None:
        item = self._pending_item(item_id)
        cleaned = text(reason, "驳回原因", max_len=200)
        assert_item_transition(item.status, ItemStatus.REJECTED)
        with transaction() as connection:
            changed = ItemRepository(connection).change_status(
                item_id,
                ItemStatus.PENDING_REVIEW.value,
                ItemStatus.REJECTED.value,
                expected_version=expected_version,
            )
            if changed == 0:
                raise StateConflict("数据已变化，请刷新后重试")
            AuditRepository(connection).insert(
                item_id, admin_id, AuditResult.REJECTED.value, cleaned
            )
            LogRepository(connection).insert(
                operator_id=admin_id,
                operator_type="USER",
                target_type="ITEM",
                target_id=item_id,
                action=LogAction.ITEM_REJECT,
                detail=f"审核驳回：{cleaned}",
            )

    def violation_delist(self, admin_id: int, item_id: int, reason: str,
                         expected_version: int | None = None) -> None:
        """违规下架：取消有效预约、商品终态、两条日志在同一事务内完成。"""

        cleaned = text(reason, "下架原因", max_len=200)
        item = ItemRepository(self.connection).find_by_id(item_id)
        if item is None:
            raise NotFound("商品不存在")
        if item.status not in {ItemStatus.PUBLISHED, ItemStatus.RESERVED}:
            raise StateConflict(f"商品当前为“{item.status.label}”，不能违规下架")
        if expected_version is not None and expected_version != item.version:
            raise StateConflict("数据已变化，请刷新后重试")
        assert_item_transition(item.status, ItemStatus.VIOLATION_DELISTED)

        with transaction() as connection:
            reservation_repo = ReservationRepository(connection)
            active = reservation_repo.find_active_by_item(item_id)
            if active is not None:
                cancelled = reservation_repo.change_status(
                    active.reservation_id,
                    active.status.value,
                    "CANCELLED",
                    expected_version=active.version,
                    cancel_reason="商品被下架",
                )
                if cancelled == 0:
                    raise StateConflict("预约状态已变化，请刷新后重试")
                LogRepository(connection).insert(
                    operator_id=admin_id,
                    operator_type="USER",
                    target_type="RESERVATION",
                    target_id=active.reservation_id,
                    action=LogAction.RESERVATION_CANCEL,
                    detail="管理员违规下架，联动取消预约",
                )

            changed = ItemRepository(connection).change_status(
                item_id,
                item.status.value,
                ItemStatus.VIOLATION_DELISTED.value,
                expected_version=item.version,
            )
            if changed == 0:
                raise StateConflict("数据已变化，请刷新后重试")
            LogRepository(connection).insert(
                operator_id=admin_id,
                operator_type="USER",
                target_type="ITEM",
                target_id=item_id,
                action=LogAction.ITEM_VIOLATION,
                detail=f"违规下架：{cleaned}",
            )

    def pending_list(self, page: Page) -> list[Item]:
        repo = ItemRepository(self.connection)
        page.total = repo.count_pending_review()
        return repo.list_pending_review(page.page_size, page.offset)

    def admin_list(self, status: str | None, keyword: str,
                   page: Page) -> list[Item]:
        repo = ItemRepository(self.connection)
        page.total = repo.count_for_admin(status, keyword)
        return repo.list_for_admin(status, keyword, page.page_size, page.offset)

    def latest_audit(self, item_id: int):
        return AuditRepository(self.connection).latest_for_item(item_id)
