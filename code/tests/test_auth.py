"""账号、密码与登录锁定测试（REQ-001/022）。"""

from __future__ import annotations

import pytest

from secondhand.domain.errors import AccountLocked, AuthError, ValidationError
from secondhand.services.auth_service import AuthService


def test_register_and_login(db):
    service = AuthService(db)
    user = service.register("newuser", "13900000001", "Passw0rd", "新同学")
    assert user.username == "newuser"
    assert user.nickname == "新同学"
    logged = service.login("newuser", "Passw0rd")
    assert logged.user_id == user.user_id
    assert service.login("13900000001", "Passw0rd").user_id == user.user_id


def test_duplicate_username_and_phone(db):
    service = AuthService(db)
    service.register("dupuser", "13900000002", "Passw0rd")
    with pytest.raises(ValidationError):
        service.register("dupuser", "13900000003", "Passw0rd")
    with pytest.raises(ValidationError):
        service.register("otheruser", "13900000002", "Passw0rd")


@pytest.mark.parametrize(
    ("username", "phone", "password"),
    [
        ("ab", "13900000004", "Passw0rd"),
        ("bad user", "13900000004", "Passw0rd"),
        ("okuser", "12345", "Passw0rd"),
        ("okuser2", "13900000005", "short"),
        ("okuser3", "13900000006", "12345678"),
        ("okuser4", "13900000007", "abcdefgh"),
    ],
)
def test_register_validation(db, username, phone, password):
    with pytest.raises(ValidationError):
        AuthService(db).register(username, phone, password)


def test_password_is_hashed(db):
    AuthService(db).register("hashuser", "13900000008", "Passw0rd")
    row = db.execute(
        "SELECT password_hash FROM user WHERE username = 'hashuser'"
    ).fetchone()
    assert row["password_hash"] != "Passw0rd"
    assert row["password_hash"].startswith("$2b$")


def test_login_failure_locks_account(db):
    service = AuthService(db)
    service.register("lockuser", "13900000009", "Passw0rd")
    for _ in range(4):
        with pytest.raises(AuthError):
            service.login("lockuser", "wrong-pass1")
    with pytest.raises(AccountLocked):
        service.login("lockuser", "wrong-pass1")
    with pytest.raises(AccountLocked):
        service.login("lockuser", "Passw0rd")
    row = db.execute(
        "SELECT failed_attempts, locked_until FROM user WHERE username = 'lockuser'"
    ).fetchone()
    assert row["failed_attempts"] == 5
    assert row["locked_until"] is not None


def test_success_resets_failed_attempts(db):
    service = AuthService(db)
    service.register("resetuser", "13900000010", "Passw0rd")
    for _ in range(2):
        with pytest.raises(AuthError):
            service.login("resetuser", "bad-pass1")
    assert service.login("resetuser", "Passw0rd").username == "resetuser"
    row = db.execute(
        "SELECT failed_attempts, locked_until FROM user WHERE username = 'resetuser'"
    ).fetchone()
    assert row["failed_attempts"] == 0
    assert row["locked_until"] is None


def test_unknown_user_login_does_not_leak(db):
    with pytest.raises(AuthError) as info:
        AuthService(db).login("nobody", "Passw0rd")
    assert "用户名或密码错误" in info.value.message
