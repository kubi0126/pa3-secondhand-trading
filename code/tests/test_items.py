"""商品生命周期、审核、版本与可见性测试。"""

from __future__ import annotations

import pytest

from secondhand.domain.enums import ItemStatus
from secondhand.domain.errors import PermissionDenied, StateConflict, ValidationError
from secondhand.repositories.audit_repo import AuditRepository
from secondhand.repositories.item_repo import ItemRepository
from secondhand.repositories.reservation_repo import ReservationRepository
from secondhand.services.audit_service import AuditService
from secondhand.services.auth_service import AuthService
from secondhand.services.dto import ItemInput
from secondhand.services.item_service import ItemService
from secondhand.services.reservation_service import ReservationService


def _input(title="测试商品", price="88.00", image_url="", description="测试描述"):
    return ItemInput(
        title=title,
        description=description,
        category_id=1,
        condition_id=1,
        price=price,
        image_url=image_url,
    )


def test_create_submit_approve(db, alice_id, admin_user_id):
    service = ItemService(db)
    item_id = service.create_draft(alice_id, _input("生命周期测试"))
    item = ItemRepository(db).find_by_id(item_id)
    assert item.status is ItemStatus.DRAFT
    assert item.version == 0

    service.submit(alice_id, item_id, 0)
    item = ItemRepository(db).find_by_id(item_id)
    assert item.status is ItemStatus.PENDING_REVIEW
    assert item.version == 1

    AuditService(db).approve(admin_user_id, item_id, 1)
    item = ItemRepository(db).find_by_id(item_id)
    assert item.status is ItemStatus.PUBLISHED
    assert item.published_at is not None
    audits = AuditRepository(db).list_by_item(item_id)
    assert len(audits) == 1
    assert audits[0].result.value == "APPROVED"


def test_key_change_triggers_review(db, alice_id, make_published_item):
    item_id = make_published_item(alice_id, "改价测试")
    item = ItemRepository(db).find_by_id(item_id)
    new_status = ItemService(db).update(
        alice_id, item_id, _input("改价测试", "99.00"), item.version
    )
    assert new_status is ItemStatus.PENDING_REVIEW
    item = ItemRepository(db).find_by_id(item_id)
    assert item.status is ItemStatus.PENDING_REVIEW
    assert item.version == 3


def test_description_only_change_keeps_published(db, alice_id, make_published_item):
    item_id = make_published_item(alice_id, "描述测试")
    item = ItemRepository(db).find_by_id(item_id)
    new_status = ItemService(db).update(
        alice_id, item_id, _input("描述测试", description="只改描述"), item.version
    )
    assert new_status is ItemStatus.PUBLISHED
    assert ItemRepository(db).find_by_id(item_id).status is ItemStatus.PUBLISHED


def test_old_version_conflict(db, alice_id, make_published_item):
    item_id = make_published_item(alice_id, "版本测试")
    item = ItemRepository(db).find_by_id(item_id)
    ItemService(db).update(
        alice_id, item_id, _input("版本测试", description="第一次修改"), item.version
    )
    with pytest.raises(StateConflict):
        ItemService(db).update(
            alice_id, item_id, _input("版本测试", description="旧页面修改"), item.version
        )


def test_audit_reject_requires_reason(db, alice_id, admin_user_id):
    service = ItemService(db)
    item_id = service.create_draft(alice_id, _input("驳回测试"))
    service.submit(alice_id, item_id, 0)
    with pytest.raises(ValidationError):
        AuditService(db).reject(admin_user_id, item_id, "  ", 1)
    AuditService(db).reject(admin_user_id, item_id, "图片不清晰", 1)
    item = ItemRepository(db).find_by_id(item_id)
    assert item.status is ItemStatus.REJECTED
    latest = AuditRepository(db).latest_for_item(item_id)
    assert latest.reason == "图片不清晰"


def test_delist_blocked_by_active_reservation(db, alice_id, bob_id, make_published_item):
    item_id = make_published_item(alice_id, "下架冲突")
    item = ItemRepository(db).find_by_id(item_id)
    ReservationService(db).create(bob_id, item_id, "delist-req", item.version)
    with pytest.raises(StateConflict):
        ItemService(db).delist(alice_id, item_id, item.version + 1)


def test_delist_is_terminal(db, alice_id, make_published_item):
    item_id = make_published_item(alice_id, "下架终态")
    item = ItemRepository(db).find_by_id(item_id)
    ItemService(db).delist(alice_id, item_id, item.version)
    assert ItemRepository(db).find_by_id(item_id).status is ItemStatus.DELISTED
    with pytest.raises(StateConflict):
        ItemService(db).submit(alice_id, item_id, item.version + 1)


def test_visibility_rules(db, alice_id, bob_id, make_published_item):
    service = ItemService(db)
    draft_id = service.create_draft(alice_id, _input("不可见草稿"))
    with pytest.raises(PermissionDenied):
        service.get_detail(draft_id, None)
    bob = AuthService(db).login("bob", "User@123")
    alice = AuthService(db).login("alice", "User@123")
    with pytest.raises(PermissionDenied):
        service.get_detail(draft_id, bob)
    assert service.get_detail(draft_id, alice)["item"].item_id == draft_id

    sold_id = make_published_item(alice_id, "已售出可见性")
    item = ItemRepository(db).find_by_id(sold_id)
    ReservationService(db).create(bob_id, sold_id, "sold-vis-req", item.version)
    reservation = ReservationRepository(db).find_active_by_item(sold_id)
    ReservationService(db).confirm(alice_id, reservation.reservation_id, reservation.version)
    reservation = ReservationService(db).get(reservation.reservation_id)
    ReservationService(db).complete(alice_id, reservation.reservation_id, reservation.version)
    with pytest.raises(PermissionDenied):
        service.get_detail(sold_id, None)
    assert service.get_detail(sold_id, bob)["item"].status is ItemStatus.SOLD


def test_invalid_price_and_url(db, alice_id):
    service = ItemService(db)
    for price in ("0", "-1", "abc"):
        with pytest.raises(ValidationError):
            service.create_draft(alice_id, _input("价格测试", price))
    with pytest.raises(ValidationError):
        service.create_draft(alice_id, _input("图片测试", image_url="ftp://example.com/a.png"))
