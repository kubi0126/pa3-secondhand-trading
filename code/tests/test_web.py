"""页面、权限与 CSRF 的 Web 层测试。"""

from __future__ import annotations

from secondhand.domain.enums import ItemStatus, ReservationStatus
from secondhand.repositories.item_repo import ItemRepository
from secondhand.repositories.reservation_repo import ReservationRepository
from secondhand.services.dto import ItemInput
from secondhand.services.item_service import ItemService
from secondhand.services.reservation_service import ReservationService


def _login(client, username="alice", password="User@123"):
    return client.post(
        "/login",
        data={"login": username, "password": password},
        follow_redirects=True,
    )


def test_public_pages(client):
    for path in ("/", "/login", "/register"):
        response = client.get(path)
        assert response.status_code == 200
        assert "校园二手" in response.get_data(as_text=True)


def test_login_and_seller_pages(client):
    response = _login(client)
    assert response.status_code == 200
    for path in ("/my/items", "/my/reservations", "/seller/reservations", "/seller/logs"):
        assert client.get(path).status_code == 200
    assert client.get("/items/new").status_code == 200


def test_non_admin_cannot_open_admin_pages(client):
    _login(client, "alice", "User@123")
    response = client.get("/admin/review", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_admin_pages(client):
    _login(client, "admin", "Admin@123")
    for path in ("/admin/review", "/admin/items", "/admin/logs", "/admin/stats", "/admin/dict"):
        assert client.get(path).status_code == 200


def test_buyer_pages(client):
    _login(client, "bob", "User@123")
    assert client.get("/my/reservations").status_code == 200


def test_csrf_rejects_post_without_token(client, app):
    app.config["CSRF_ENABLED"] = True
    try:
        response = client.post(
            "/login", data={"login": "alice", "password": "User@123"}
        )
        assert response.status_code == 400
    finally:
        app.config["CSRF_ENABLED"] = False


def test_create_item_via_form(client, db):
    _login(client)
    response = client.post(
        "/items/new",
        data={
            "title": "表单创建测试",
            "description": "通过页面创建",
            "category_id": "1",
            "condition_id": "1",
            "price": "12.50",
            "image_url": "",
            "action": "save",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "草稿已保存" in response.get_data(as_text=True)
    row = db.execute("SELECT status FROM item WHERE title = '表单创建测试'").fetchone()
    assert row["status"] == "DRAFT"


def test_draft_detail_forbidden_for_other_user(client, db, alice_id):
    item_id = ItemService(db).create_draft(
        alice_id,
        ItemInput("私有草稿", "描述", 1, 1, "10", ""),
    )
    _login(client, "bob", "User@123")
    response = client.get(f"/items/{item_id}")
    assert response.status_code == 403
    assert "仅卖家本人和管理员可见" in response.get_data(as_text=True)


def test_missing_item_returns_404(client):
    response = client.get("/items/999999")
    assert response.status_code == 404


def test_admin_approve_via_web(client, db, alice_id):
    item_id = ItemService(db).create_draft(
        alice_id, ItemInput("网页审核", "描述", 1, 1, "10", "")
    )
    ItemService(db).submit(alice_id, item_id, 0)
    _login(client, "admin", "Admin@123")
    response = client.post(
        f"/admin/review/{item_id}/approve",
        data={"version": "1"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "审核通过" in response.get_data(as_text=True)
    assert ItemRepository(db).find_by_id(item_id).status is ItemStatus.PUBLISHED


def test_admin_violation_via_web(client, db, alice_id, bob_id, make_published_item):
    item_id = make_published_item(alice_id, "网页违规下架")
    item = ItemRepository(db).find_by_id(item_id)
    reservation_id = ReservationService(db).create(
        bob_id, item_id, "web-violation", item.version
    )
    item = ItemRepository(db).find_by_id(item_id)
    _login(client, "admin", "Admin@123")
    response = client.post(
        f"/admin/items/{item_id}/violation",
        data={"reason": "网页违规测试", "version": str(item.version)},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "已违规下架" in response.get_data(as_text=True)
    assert ItemRepository(db).find_by_id(item_id).status is ItemStatus.VIOLATION_DELISTED
    assert (
        ReservationService(db).get(reservation_id).status
        is ReservationStatus.CANCELLED
    )


def test_dict_create_and_toggle(client, db):
    _login(client, "admin", "Admin@123")
    response = client.post(
        "/admin/dict/category",
        data={"op": "create", "name": "乐器", "sort_order": "60"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    row = db.execute("SELECT category_id, enabled FROM category WHERE name = '乐器'").fetchone()
    assert row is not None and row["enabled"] == 1
    client.post(
        "/admin/dict/category",
        data={"op": "toggle", "category_id": str(row["category_id"])},
        follow_redirects=True,
    )
    row = db.execute("SELECT enabled FROM category WHERE name = '乐器'").fetchone()
    assert row["enabled"] == 0


def test_seller_confirm_and_complete_via_web(client, db, alice_id, bob_id,
                                             make_published_item):
    item_id = make_published_item(alice_id, "网页完成交易")
    item = ItemRepository(db).find_by_id(item_id)
    reservation_id = ReservationService(db).create(
        bob_id, item_id, "web-complete", item.version
    )
    _login(client, "alice", "User@123")
    reservation = ReservationService(db).get(reservation_id)
    client.post(
        f"/seller/reservations/{reservation_id}/confirm",
        data={"version": str(reservation.version)},
        follow_redirects=True,
    )
    reservation = ReservationService(db).get(reservation_id)
    assert reservation.status is ReservationStatus.CONFIRMED
    response = client.post(
        f"/seller/reservations/{reservation_id}/complete",
        data={"version": str(reservation.version)},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "交易已完成" in response.get_data(as_text=True)
    assert ItemRepository(db).find_by_id(item_id).status is ItemStatus.SOLD


def test_buyer_reserve_and_cancel_via_web(client, db, alice_id, make_published_item):
    item_id = make_published_item(alice_id, "网页预约取消")
    _login(client, "bob", "User@123")
    response = client.post(
        f"/items/{item_id}/reserve",
        data={"request_id": "web-reserve", "version": "2"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "预约已创建" in response.get_data(as_text=True)
    reservation = ReservationRepository(db).find_active_by_item(item_id)
    assert reservation is not None
    response = client.post(
        f"/reservations/{reservation.reservation_id}/cancel",
        data={"version": str(reservation.version)},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "预约已取消" in response.get_data(as_text=True)
    assert ItemRepository(db).find_by_id(item_id).status is ItemStatus.PUBLISHED
