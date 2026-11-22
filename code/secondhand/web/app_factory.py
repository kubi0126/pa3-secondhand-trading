"""Flask 应用工厂：配置、数据库、蓝图、模板与错误处理。"""

from __future__ import annotations

from flask import Flask, flash, g, redirect, render_template, request, session, url_for
from werkzeug.exceptions import HTTPException

from ..config import Config
from ..db import get_db, init_app as init_db
from ..cli import register_cli
from ..domain.enums import (
    AuditResult,
    ItemStatus,
    ReservationStatus,
    Role,
)
from ..domain.errors import AppError
from ..repositories.log_repo import LOG_ACTION_LABELS
from ..repositories.user_repo import UserRepository
from ..seed import seed_database
from ..utils import human_time, now, remaining_text
from .csrf import csrf_token, validate_csrf
from .routes_admin import admin_bp
from .routes_auth import auth_bp
from .routes_buyer import buyer_bp
from .routes_items import items_bp
from .routes_seller import seller_bp


def create_app(overrides: dict | None = None) -> Flask:
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
        static_url_path="/static",
    )
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)

    init_db(app)
    with app.app_context():
        app.extensions["db"].init_schema()
        if app.config.get("SEED_DATA", True):
            connection = app.extensions["db"].connect()
            try:
                seed_database(connection)
            finally:
                connection.close()

    app.register_blueprint(auth_bp)
    app.register_blueprint(items_bp)
    app.register_blueprint(buyer_bp)
    app.register_blueprint(seller_bp)
    app.register_blueprint(admin_bp)
    register_cli(app)

    @app.before_request
    def load_current_user() -> None:
        user_id = session.get("user_id")
        g.user = None
        if user_id:
            user = UserRepository(get_db()).find_by_id(int(user_id))
            if user is None:
                session.clear()
            else:
                g.user = user
        validate_csrf()

    @app.context_processor
    def inject_globals() -> dict:
        def page_url(target: int) -> str:
            args = request.args.to_dict(flat=True)
            args["page"] = target
            return url_for(request.endpoint or "items.index",
                           **(request.view_args or {}), **args)

        return {
            "current_user": getattr(g, "user", None),
            "csrf_token": csrf_token,
            "now": now,
            "page_url": page_url,
            "ItemStatus": ItemStatus,
            "ReservationStatus": ReservationStatus,
            "Role": Role,
            "AuditResult": AuditResult,
            "log_action_labels": LOG_ACTION_LABELS,
        }

    @app.template_filter("dt")
    def format_datetime(value: str | None) -> str:
        return human_time(value)

    @app.template_filter("money")
    def format_money(value: float | None) -> str:
        if value is None:
            return "-"
        return f"{value:,.2f}"

    @app.template_filter("remaining")
    def format_remaining(value: str | None) -> str:
        return remaining_text(value)

    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        if request.method == "POST":
            flash(error.message, "error")
            return redirect(request.referrer or url_for("items.index"))
        return (
            render_template(
                "errors/error.html", error=error, status_code=error.status_code
            ),
            error.status_code,
        )

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        return (
            render_template(
                "errors/error.html",
                error=AppError(error.description or "请求处理失败"),
                status_code=error.code,
            ),
            error.code,
        )

    @app.errorhandler(Exception)
    def handle_unexpected(error: Exception):
        if app.config.get("TESTING"):
            raise error
        app.logger.exception("unhandled error: %s", error)
        return (
            render_template(
                "errors/error.html",
                error=AppError("服务器内部错误，请稍后重试"),
                status_code=500,
            ),
            500,
        )

    return app
