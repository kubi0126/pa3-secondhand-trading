"""预约与交易服务：先到先得、幂等、乐观锁、超时与联动。"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from ..db import transaction
from ..domain.enums import ItemStatus, ReservationStatus
from ..domain.errors import (
    DuplicateRequest,
    NotFound,
    PermissionDenied,
    StateConflict,
    ValidationError,
)
from ..domain.models import Reservation
from ..domain.state_machines import assert_reservation_transition
from ..repositories.item_repo import ItemRepository
from ..repositories.log_repo import LogAction, LogRepository
from ..repositories.request_repo import RequestRepository
from ..repositories.reservation_repo import ReservationRepository
from ..utils import Page, fmt, hours_later, now, parse, seconds_later, text

ACTIVE_STATUSES = (ReservationStatus.PENDING_CONFIRM, ReservationStatus.CONFIRMED)


class ReservationService:
    def __init__(self, connection: sqlite3.Connection, *, confirm_hours: int = 24,
                 complete_hours: int = 48, duplicate_seconds: int = 60) -> None:
        self.connection = connection
        self.confirm_hours = confirm_hours
        self.complete_hours = complete_hours
        self.duplicate_seconds = duplicate_seconds

    # ---------- 内部工具 ----------
    @staticmethod
    def _result_id(request_row) -> int | None:
        if not request_row or not request_row.result_json:
            return None
        try:
            data = json.loads(request_row.result_json)
        except (TypeError, ValueError):
            return None
        value = data.get("reservation_id")
        return int(value) if value is not None else None

    def _start_request(self, connection: sqlite3.Connection, request_id: str,
                       buyer_id: int, endpoint: str) -> None:
        """在同一写事务中占位；已成功的请求直接抛出“返回首次结果”的信号。"""

        repo = RequestRepository(connection)
        existing = repo.find(request_id)
        if existing is None:
            if repo.try_start(request_id, buyer_id, endpoint):
                return
            existing = repo.find(request_id)
        if existing is None:
            raise DuplicateRequest("请求正在处理中，请稍后刷新")
        if existing.user_id != buyer_id:
            raise PermissionDenied("请求标识不属于当前用户")
        if existing.status == "SUCCESS":
            reservation_id = self._result_id(existing)
            if reservation_id is None:
                raise DuplicateRequest("该请求已处理，请刷新列表")
            raise _AlreadyProcessed(reservation_id)
        if existing.status == "PROCESSING":
            raise DuplicateRequest("请求正在处理中，请稍后刷新")
        repo.restart(request_id)

    def _release_item(self, connection: sqlite3.Connection, item_id: int) -> None:
        """预约结束释放商品：只有处于“已预约”的商品恢复为“已发布”。"""

        item = ItemRepository(connection).find_by_id(item_id)
        if item is None or item.status is not ItemStatus.RESERVED:
            return
        changed = ItemRepository(connection).change_status(
            item_id, ItemStatus.RESERVED.value, ItemStatus.PUBLISHED.value,
            expected_version=item.version,
        )
        if changed == 0:
            raise StateConflict("商品状态已变化，请刷新后重试")

    @staticmethod
    def _require_buyer(reservation: Reservation, buyer_id: int) -> None:
        if reservation.buyer_id != buyer_id:
            raise PermissionDenied("只能操作自己的预约")

    @staticmethod
    def _require_seller(reservation: Reservation, seller_id: int) -> None:
        if reservation.seller_id != seller_id:
            raise PermissionDenied("只能处理自己商品的预约")

    # ---------- 创建预约 ----------
    def create(self, buyer_id: int, item_id: int, request_id: str,
               expected_version: int | None = None) -> int:
        request_id = (request_id or "").strip()
        if not request_id:
            raise ValidationError("缺少请求标识，请刷新页面后重试")
        if len(request_id) > 64:
            raise ValidationError("请求标识过长")

        try:
            with transaction() as connection:
                self._start_request(connection, request_id, buyer_id, "reservation.create")
                item = ItemRepository(connection).find_by_id(item_id)
                if item is None:
                    raise NotFound("商品不存在")
                if item.seller_id == buyer_id:
                    raise PermissionDenied("不能预约自己发布的商品")
                reservation_repo = ReservationRepository(connection)
                since = fmt(seconds_later(now(), -self.duplicate_seconds))
                recent = reservation_repo.find_recent_by_buyer_item(
                    buyer_id, item_id, since
                )
                if recent is not None:
                    RequestRepository(connection).mark_success(
                        request_id, json.dumps({"reservation_id": recent.reservation_id})
                    )
                    return recent.reservation_id

                if item.status is ItemStatus.RESERVED:
                    raise StateConflict("商品已被预约")
                if item.status is not ItemStatus.PUBLISHED:
                    raise StateConflict(f"商品当前为“{item.status.label}”，不能预约")
                version = item.version if expected_version is None else expected_version
                if version != item.version:
                    raise StateConflict("数据已变化，请刷新后重试")

                active = reservation_repo.find_active_by_item(item_id)
                if active is not None:
                    raise StateConflict("商品已被预约")

                expire_at = fmt(hours_later(now(), self.confirm_hours))
                reservation_id = reservation_repo.insert(
                    item_id, buyer_id, request_id, expire_at
                )
                changed = ItemRepository(connection).change_status(
                    item_id,
                    ItemStatus.PUBLISHED.value,
                    ItemStatus.RESERVED.value,
                    expected_version=item.version,
                )
                if changed == 0:
                    raise StateConflict("商品已被其他买家预约")
                LogRepository(connection).insert(
                    operator_id=buyer_id,
                    operator_type="USER",
                    target_type="RESERVATION",
                    target_id=reservation_id,
                    action=LogAction.RESERVATION_CREATE,
                    detail=f"预约商品：{item.title}",
                )
                RequestRepository(connection).mark_success(
                    request_id, json.dumps({"reservation_id": reservation_id})
                )
                return reservation_id
        except _AlreadyProcessed as exc:
            return exc.reservation_id
        except sqlite3.IntegrityError as exc:
            raise StateConflict("商品已被预约，请刷新后重试") from exc

    # ---------- 买家取消 ----------
    def cancel(self, buyer_id: int, reservation_id: int,
               expected_version: int) -> None:
        reservation = ReservationRepository(self.connection).find_by_id(reservation_id)
        if reservation is None:
            raise NotFound("预约不存在")
        self._require_buyer(reservation, buyer_id)
        if reservation.status not in ACTIVE_STATUSES:
            raise StateConflict(f"预约当前为“{reservation.status.label}”，不能取消")
        assert_reservation_transition(reservation.status, ReservationStatus.CANCELLED)

        with transaction() as connection:
            changed = ReservationRepository(connection).change_status(
                reservation_id,
                reservation.status.value,
                ReservationStatus.CANCELLED.value,
                expected_version=expected_version,
                cancel_reason="买家主动取消",
            )
            if changed == 0:
                raise StateConflict("数据已变化，请刷新后重试")
            self._release_item(connection, reservation.item_id)
            LogRepository(connection).insert(
                operator_id=buyer_id,
                operator_type="USER",
                target_type="RESERVATION",
                target_id=reservation_id,
                action=LogAction.RESERVATION_CANCEL,
                detail="买家取消预约",
            )

    # ---------- 卖家拒绝 ----------
    def reject(self, seller_id: int, reservation_id: int, reason: str,
               expected_version: int) -> None:
        reservation = ReservationRepository(self.connection).find_by_id(reservation_id)
        if reservation is None:
            raise NotFound("预约不存在")
        self._require_seller(reservation, seller_id)
        if reservation.status is not ReservationStatus.PENDING_CONFIRM:
            raise StateConflict(f"预约当前为“{reservation.status.label}”，不能拒绝")
        cleaned = text(reason, "拒绝原因", max_len=200)
        assert_reservation_transition(reservation.status, ReservationStatus.REJECTED)

        with transaction() as connection:
            changed = ReservationRepository(connection).change_status(
                reservation_id,
                reservation.status.value,
                ReservationStatus.REJECTED.value,
                expected_version=expected_version,
                cancel_reason=cleaned,
            )
            if changed == 0:
                raise StateConflict("数据已变化，请刷新后重试")
            self._release_item(connection, reservation.item_id)
            LogRepository(connection).insert(
                operator_id=seller_id,
                operator_type="USER",
                target_type="RESERVATION",
                target_id=reservation_id,
                action=LogAction.RESERVATION_REJECT,
                detail=f"卖家拒绝预约：{cleaned}",
            )

    # ---------- 卖家确认 ----------
    def confirm(self, seller_id: int, reservation_id: int,
                expected_version: int) -> None:
        reservation = ReservationRepository(self.connection).find_by_id(reservation_id)
        if reservation is None:
            raise NotFound("预约不存在")
        self._require_seller(reservation, seller_id)
        if reservation.status is not ReservationStatus.PENDING_CONFIRM:
            raise StateConflict(f"预约当前为“{reservation.status.label}”，不能确认")
        if parse(reservation.expire_at) and parse(reservation.expire_at) <= now():
            raise StateConflict("预约已超时，请刷新列表")
        assert_reservation_transition(reservation.status, ReservationStatus.CONFIRMED)

        with transaction() as connection:
            changed = ReservationRepository(connection).change_status(
                reservation_id,
                reservation.status.value,
                ReservationStatus.CONFIRMED.value,
                expected_version=expected_version,
                confirmed_at=fmt(now()),
                expire_at=fmt(hours_later(now(), self.complete_hours)),
            )
            if changed == 0:
                raise StateConflict("数据已变化，请刷新后重试")
            LogRepository(connection).insert(
                operator_id=seller_id,
                operator_type="USER",
                target_type="RESERVATION",
                target_id=reservation_id,
                action=LogAction.RESERVATION_CONFIRM,
                detail="卖家确认预约，等待线下交易",
            )

    # ---------- 卖家标记完成 ----------
    def complete(self, seller_id: int, reservation_id: int,
                 expected_version: int) -> None:
        reservation = ReservationRepository(self.connection).find_by_id(reservation_id)
        if reservation is None:
            raise NotFound("预约不存在")
        self._require_seller(reservation, seller_id)
        if reservation.status is not ReservationStatus.CONFIRMED:
            raise StateConflict(f"预约当前为“{reservation.status.label}”，不能完成")
        if parse(reservation.expire_at) and parse(reservation.expire_at) <= now():
            raise StateConflict("预约已超时，请刷新列表")
        assert_reservation_transition(reservation.status, ReservationStatus.COMPLETED)

        with transaction() as connection:
            changed = ReservationRepository(connection).change_status(
                reservation_id,
                reservation.status.value,
                ReservationStatus.COMPLETED.value,
                expected_version=expected_version,
                completed_at=fmt(now()),
            )
            if changed == 0:
                raise StateConflict("数据已变化，请刷新后重试")
            item = ItemRepository(connection).find_by_id(reservation.item_id)
            if item is None or item.status is not ItemStatus.RESERVED:
                raise StateConflict("商品状态已变化，请刷新后重试")
            item_changed = ItemRepository(connection).change_status(
                reservation.item_id,
                ItemStatus.RESERVED.value,
                ItemStatus.SOLD.value,
                expected_version=item.version,
            )
            if item_changed == 0:
                raise StateConflict("商品状态已变化，请刷新后重试")
            LogRepository(connection).insert(
                operator_id=seller_id,
                operator_type="USER",
                target_type="RESERVATION",
                target_id=reservation_id,
                action=LogAction.RESERVATION_COMPLETE,
                detail="线下交易完成，商品售出",
            )

    # ---------- 定时过期 ----------
    def expire_due(self) -> int:
        due = ReservationRepository(self.connection).list_due(fmt(now()))
        expired = 0
        for candidate in due:
            try:
                with transaction() as connection:
                    repo = ReservationRepository(connection)
                    reservation = repo.find_by_id(candidate.reservation_id)
                    if reservation is None or reservation.status not in ACTIVE_STATUSES:
                        continue
                    reason = (
                        "卖家 24 小时未确认"
                        if reservation.status is ReservationStatus.PENDING_CONFIRM
                        else "卖家 48 小时未完成交易"
                    )
                    changed = repo.change_status(
                        reservation.reservation_id,
                        reservation.status.value,
                        ReservationStatus.EXPIRED.value,
                        expected_version=reservation.version,
                        cancel_reason=reason,
                    )
                    if changed == 0:
                        continue
                    self._release_item(connection, reservation.item_id)
                    LogRepository(connection).insert(
                        operator_id=None,
                        operator_type="SYSTEM",
                        target_type="RESERVATION",
                        target_id=reservation.reservation_id,
                        action=LogAction.RESERVATION_EXPIRE,
                        detail=reason,
                    )
                    expired += 1
            except (StateConflict, sqlite3.IntegrityError):
                continue
        return expired

    # ---------- 查询 ----------
    def list_my(self, buyer_id: int, status: str | None, page: Page) -> list[Reservation]:
        self._validate_status(status)
        repo = ReservationRepository(self.connection)
        page.total = repo.count_by_buyer(buyer_id, status)
        return repo.list_by_buyer(buyer_id, status, page.page_size, page.offset)

    def list_pending(self, seller_id: int, page: Page) -> list[Reservation]:
        repo = ReservationRepository(self.connection)
        page.total = repo.count_pending_by_seller(seller_id)
        return repo.list_pending_by_seller(seller_id, page.page_size, page.offset)

    def list_seller(self, seller_id: int, status: str | None,
                    page: Page) -> list[Reservation]:
        self._validate_status(status)
        repo = ReservationRepository(self.connection)
        page.total = repo.count_by_seller(seller_id, status)
        return repo.list_by_seller(seller_id, status, page.page_size, page.offset)

    def get(self, reservation_id: int) -> Reservation:
        reservation = ReservationRepository(self.connection).find_by_id(reservation_id)
        if reservation is None:
            raise NotFound("预约不存在")
        return reservation

    @staticmethod
    def _validate_status(status: str | None) -> None:
        if status is None:
            return
        try:
            ReservationStatus(status)
        except ValueError as exc:
            raise ValidationError("预约状态参数不正确") from exc


class _AlreadyProcessed(Exception):
    """内部信号：幂等命中，直接返回首次预约 ID。"""

    def __init__(self, reservation_id: int) -> None:
        super().__init__("already processed")
        self.reservation_id = reservation_id
