"""会话登录状态与权限装饰器。"""

from __future__ import annotations

from functools import wraps
from typing import Callable

from flask import flash, g, redirect, request, session, url_for

from ..domain.enums import Role
from ..domain.models import User


def login_user(user: User) -> None:
    session.clear()
    session["user_id"] = user.user_id
    session["role"] = user.role.value


def logout_user() -> None:
    session.clear()


def current_user() -> User | None:
    return getattr(g, "user", None)


def login_required(view: Callable) -> Callable:
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            flash("请先登录", "warning")
            return redirect(url_for("auth.login", next=request.full_path))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view: Callable) -> Callable:
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if user is None:
            flash("请先登录", "warning")
            return redirect(url_for("auth.login", next=request.full_path))
        if user.role is not Role.ADMIN:
            flash("该操作仅管理员可用", "error")
            return redirect(url_for("items.index"))
        return view(*args, **kwargs)

    return wrapped


def seller_required(view: Callable) -> Callable:
    """普通用户即可发布商品；管理员不参与卖家操作。"""

    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if user is None:
            flash("请先登录", "warning")
            return redirect(url_for("auth.login", next=request.full_path))
        if user.role is Role.ADMIN:
            flash("管理员不参与商品发布与预约处理", "error")
            return redirect(url_for("admin.review"))
        return view(*args, **kwargs)

    return wrapped
