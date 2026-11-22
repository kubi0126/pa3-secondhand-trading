"""预约生命周期、幂等、超时与联动测试。"""

from __future__ import annotations

import pytest

from secondhand.domain.enums import ItemStatus, ReservationStatus
from secondhand.domain.errors import PermissionDenied, StateConflict
from secondhand.repositories.item_repo import ItemRepository
from secondhand.repositories.log_repo import LogAction
from secondhand.repositories.reservation_repo import ReservationRepository
from secondhand.services.audit_service import AuditService
from secondhand.services.reservation_service import ReservationService
from secondhand.utils import fmt, hours_later, now


def _create(db, buyer_id, item_id, request_id="req-1"):
    item = ItemRepository(db).find_by_id(item_id)
    return ReservationService(db).create(buyer_id, item_id, request_id, item.version)


def test_create_locks_item(db, alice_id, bob_id, make_published_item):
    item_id = make_published_item(alice_id, "预约锁定")
    reservation_id = _create(db, bob_id, item_id)
    item = ItemRepository(db).find_by_id(item_id)
    reservation = ReservationService(db).get(reservation_id)
    assert item.status is ItemStatus.RESERVED
    assert reservation.status is ReservationStatus.PENDING_CONFIRM
    assert reservation.item_title == "预约锁定"


def test_cannot_reserve_own_item(db, alice_id, make_published_item):
    item_id = make_published_item(alice_id, "自己的商品")
    with pytest.raises(PermissionDenied):
        _create(db, alice_id, item_id)


def test_idempotent_request_returns_same_reservation(db, alice_id, bob_id, carol_id,
                                                     make_published_item):
    item_id = make_published_item(alice_id, "幂等测试")
    first = _create(db, bob_id, item_id, "same-request")
    second = _create(db, bob_id, item_id, "same-request")
    assert first == second
    item = ItemRepository(db).find_by_id(item_id)
    assert item.status is ItemStatus.RESERVED
    with pytest.raises(StateConflict):
        _create(db, carol_id, item_id, "other-request")
    assert ReservationRepository(db).find_active_by_item(item_id).reservation_id == first


def test_cancel_releases_item(db, alice_id, bob_id, make_published_item):
    item_id = make_published_item(alice_id, "取消释放")
    reservation_id = _create(db, bob_id, item_id)
    reservation = ReservationService(db).get(reservation_id)
    ReservationService(db).cancel(bob_id, reservation_id, reservation.version)
    assert ReservationService(db).get(reservation_id).status is ReservationStatus.CANCELLED
    assert ItemRepository(db).find_by_id(item_id).status is ItemStatus.PUBLISHED


def test_reject_requires_reason_and_releases(db, alice_id, bob_id, make_published_item):
    item_id = make_published_item(alice_id, "拒绝释放")
    reservation_id = _create(db, bob_id, item_id)
    reservation = ReservationService(db).get(reservation_id)
    with pytest.raises(Exception):
        ReservationService(db).reject(alice_id, reservation_id, " ", reservation.version)
    ReservationService(db).reject(alice_id, reservation_id, "已经卖出", reservation.version)
    reservation = ReservationService(db).get(reservation_id)
    assert reservation.status is ReservationStatus.REJECTED
    assert reservation.cancel_reason == "已经卖出"
    assert ItemRepository(db).find_by_id(item_id).status is ItemStatus.PUBLISHED


def test_confirm_then_complete(db, alice_id, bob_id, make_published_item):
    item_id = make_published_item(alice_id, "确认完成")
    reservation_id = _create(db, bob_id, item_id)
    before = ReservationService(db).get(reservation_id)
    ReservationService(db).confirm(alice_id, reservation_id, before.version)
    confirmed = ReservationService(db).get(reservation_id)
    assert confirmed.status is ReservationStatus.CONFIRMED
    assert confirmed.confirmed_at is not None
    assert confirmed.expire_at != before.expire_at
    ReservationService(db).complete(alice_id, reservation_id, confirmed.version)
    assert ReservationService(db).get(reservation_id).status is ReservationStatus.COMPLETED
    assert ItemRepository(db).find_by_id(item_id).status is ItemStatus.SOLD
    assert ReservationRepository(db).find_active_by_item(item_id) is None


def test_only_owner_can_operate(db, alice_id, bob_id, carol_id, make_published_item):
    item_id = make_published_item(alice_id, "权限测试")
    reservation_id = _create(db, bob_id, item_id)
    reservation = ReservationService(db).get(reservation_id)
    with pytest.raises(PermissionDenied):
        ReservationService(db).cancel(carol_id, reservation_id, reservation.version)
    with pytest.raises(PermissionDenied):
        ReservationService(db).confirm(bob_id, reservation_id, reservation.version)


def test_expire_due_releases_item(db, alice_id, bob_id, make_published_item):
    item_id = make_published_item(alice_id, "超时测试")
    reservation_id = _create(db, bob_id, item_id)
    past = fmt(hours_later(now(), -1))
    db.execute(
        "UPDATE reservation SET expire_at = ? WHERE reservation_id = ?",
        (past, reservation_id),
    )
    expired = ReservationService(db).expire_due()
    assert expired >= 1
    reservation = ReservationService(db).get(reservation_id)
    assert reservation.status is ReservationStatus.EXPIRED
    assert "24 小时" in (reservation.cancel_reason or "")
    assert ItemRepository(db).find_by_id(item_id).status is ItemStatus.PUBLISHED
    row = db.execute(
        "SELECT operator_type, action FROM operation_log "
        "WHERE target_type = 'RESERVATION' AND target_id = ? ORDER BY log_id DESC",
        (reservation_id,),
    ).fetchone()
    assert row["operator_type"] == "SYSTEM"
    assert row["action"] == LogAction.RESERVATION_EXPIRE


def test_violation_delist_cancels_active_reservation(db, alice_id, bob_id,
                                                    admin_user_id, make_published_item):
    item_id = make_published_item(alice_id, "违规联动")
    reservation_id = _create(db, bob_id, item_id)
    AuditService(db).violation_delist(admin_user_id, item_id, "疑似假冒")
    assert ItemRepository(db).find_by_id(item_id).status is ItemStatus.VIOLATION_DELISTED
    reservation = ReservationService(db).get(reservation_id)
    assert reservation.status is ReservationStatus.CANCELLED
    assert reservation.cancel_reason == "商品被下架"
    with pytest.raises(StateConflict):
        _create(db, bob_id, item_id, "after-violation")
