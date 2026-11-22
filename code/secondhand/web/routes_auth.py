"""注册、登录与退出。"""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..db import get_db
from ..domain.errors import AppError
from ..services.auth_service import AuthService
from .auth import login_user, logout_user
from .helpers import safe_next

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        service = AuthService(get_db())
        try:
            user = service.login(request.form.get("login", ""), request.form.get("password", ""))
        except AppError as exc:
            flash(exc.message, "error")
            return render_template("auth/login.html", login=request.form.get("login", "")), exc.status_code
        login_user(user)
        flash(f"欢迎回来，{user.display_name}", "success")
        target = safe_next(request.args.get("next"))
        if target:
            return redirect(target)
        if user.is_admin:
            return redirect(url_for("admin.review"))
        return redirect(url_for("items.index"))
    return render_template("auth/login.html", login="")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        service = AuthService(get_db())
        try:
            service.register(
                username=request.form.get("username", ""),
                phone=request.form.get("phone", ""),
                password=request.form.get("password", ""),
                nickname=request.form.get("nickname", ""),
            )
        except AppError as exc:
            flash(exc.message, "error")
            return render_template(
                "auth/register.html",
                form=request.form,
            ), exc.status_code
        flash("注册成功，请登录", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form={})


@auth_bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    flash("已退出登录", "info")
    return redirect(url_for("items.index"))
