"""账号与权限服务（REQ-001/002/022）。"""

from __future__ import annotations

import sqlite3
from datetime import timedelta

from ..domain.errors import AccountLocked, AuthError, ValidationError
from ..domain.models import User
from ..repositories.user_repo import UserRepository
from ..utils import PHONE_PATTERN, USERNAME_PATTERN, fmt, now, parse
from .security import hash_password, verify_password


class AuthService:
    def __init__(self, connection: sqlite3.Connection, *, max_attempts: int = 5,
                 lock_minutes: int = 15) -> None:
        self.connection = connection
        self.max_attempts = max_attempts
        self.lock_minutes = lock_minutes

    def register(self, username: str, phone: str, password: str,
                 nickname: str | None = None) -> User:
        username = (username or "").strip()
        phone = (phone or "").strip()
        nickname = (nickname or "").strip() or None

        if not USERNAME_PATTERN.match(username):
            raise ValidationError("用户名需为 3-32 位中文、字母、数字或下划线")
        if not PHONE_PATTERN.match(phone):
            raise ValidationError("手机号格式不正确")
        if len(password or "") < 8 or len(password) > 64:
            raise ValidationError("密码长度需为 8-64 位")
        if not any(ch.isalpha() for ch in password) or not any(ch.isdigit() for ch in password):
            raise ValidationError("密码需同时包含字母和数字")

        repo = UserRepository(self.connection)
        if repo.exists_username(username):
            raise ValidationError("用户名已存在")
        if repo.exists_phone(phone):
            raise ValidationError("手机号已被注册")

        user_id = repo.insert(username, phone, hash_password(password), nickname)
        created = repo.find_by_id(user_id)
        if created is None:
            raise AuthError("注册失败，请稍后重试")
        return created

    def login(self, login: str, password: str) -> User:
        login = (login or "").strip()
        if not login or not password:
            raise AuthError("请输入用户名/手机号和密码")

        repo = UserRepository(self.connection)
        user = repo.find_by_login(login)
        if user is None:
            raise AuthError("用户名或密码错误")

        current = now()
        locked_until = parse(user.locked_until)
        if locked_until and locked_until > current:
            remain = int((locked_until - current).total_seconds() // 60) + 1
            raise AccountLocked(f"账号已锁定，请 {remain} 分钟后再试")

        if not verify_password(password, user.password_hash):
            attempts = user.failed_attempts + 1
            if attempts >= self.max_attempts:
                lock_until = current + timedelta(minutes=self.lock_minutes)
                repo.record_failed_login(user.user_id, self.max_attempts, fmt(lock_until))
                raise AccountLocked(
                    f"连续登录失败 {self.max_attempts} 次，账号已锁定 {self.lock_minutes} 分钟"
                )
            repo.record_failed_login(user.user_id, attempts, None)
            raise AuthError(f"用户名或密码错误，还可尝试 {self.max_attempts - attempts} 次")

        repo.reset_failed_login(user.user_id)
        refreshed = repo.find_by_id(user.user_id)
        return refreshed or user

    def get_user(self, user_id: int) -> User | None:
        return UserRepository(self.connection).find_by_id(user_id)
