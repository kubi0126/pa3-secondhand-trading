"""pytest 公共夹具。"""

# pylint: disable=redefined-outer-name
# 原因：pytest 通过同名参数注入夹具，这是框架约定，不是变量遮蔽。

from __future__ import annotations

import os

import pytest

from secondhand.db import get_db
from secondhand.services.audit_service import AuditService
from secondhand.services.auth_service import AuthService
from secondhand.services.dto import ItemInput
from secondhand.services.item_service import ItemService
from secondhand.web.app_factory import create_app


@pytest.fixture()
def app(tmp_path):
    os.environ["SECONDHAND_BCRYPT_ROUNDS"] = "4"
    database = tmp_path / "secondhand-test.db"
    application = create_app(
        {
            "TESTING": True,
            "DATABASE": str(database),
            "CSRF_ENABLED": False,
            "SEED_DATA": True,
            "SCHEDULER_ENABLED": False,
        }
    )
    yield application


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    with app.app_context():
        yield get_db()


@pytest.fixture()
def alice_id(db):
    return AuthService(db).login("alice", "User@123").user_id


@pytest.fixture()
def bob_id(db):
    return AuthService(db).login("bob", "User@123").user_id


@pytest.fixture()
def carol_id(db):
    return AuthService(db).login("carol", "User@123").user_id


@pytest.fixture()
def admin_user_id(db):
    return AuthService(db).login("admin", "Admin@123").user_id


@pytest.fixture()
def make_published_item(db, admin_user_id):
    def _make(seller_id: int, title: str = "测试商品", price: str = "88.00") -> int:
        service = ItemService(db)
        item_id = service.create_draft(
            seller_id,
            ItemInput(
                title=title,
                description="测试描述",
                category_id=1,
                condition_id=1,
                price=price,
                image_url="",
            ),
        )
        service.submit(seller_id, item_id, 0)
        AuditService(db).approve(admin_user_id, item_id, 1)
        return item_id

    return _make


def login(client, username: str, password: str):
    return client.post(
        "/login",
        data={"login": username, "password": password},
        follow_redirects=True,
    )


def user_id(db, username: str, password: str = "User@123") -> int:
    return AuthService(db).login(username, password).user_id


def admin_id(db) -> int:
    return AuthService(db).login("admin", "Admin@123").user_id


def create_published_item(db, seller_id: int, title: str = "测试商品",
                          price: str = "88.00") -> int:
    service = ItemService(db)
    item_id = service.create_draft(
        seller_id,
        ItemInput(
            title=title,
            description="测试描述",
            category_id=1,
            condition_id=1,
            price=price,
            image_url="",
        ),
    )
    service.submit(seller_id, item_id, 0)
    AuditService(db).approve(admin_id(db), item_id, 1)
    return item_id
