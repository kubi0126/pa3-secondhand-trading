"""Flask CLI：超时扫描与请求日志清理。"""

from __future__ import annotations

import click
from flask import Flask

from .db import get_db
from .repositories.request_repo import RequestRepository
from .services.reservation_service import ReservationService
from .utils import fmt, hours_later, now


def register_cli(app: Flask) -> None:
    @app.cli.command("expire")
    def expire_command() -> None:
        """扫描并过期超时预约。"""

        service = ReservationService(
            get_db(),
            confirm_hours=app.config["RESERVATION_CONFIRM_HOURS"],
            complete_hours=app.config["RESERVATION_COMPLETE_HOURS"],
            duplicate_seconds=app.config["DUPLICATE_RESERVATION_SECONDS"],
        )
        count = service.expire_due()
        click.echo(f"已处理 {count} 条超时预约")

    @app.cli.command("cleanup-requests")
    @click.option("--days", default=7, show_default=True, help="保留天数")
    def cleanup_requests(days: int) -> None:
        """清理过期的幂等请求记录。"""

        before = fmt(hours_later(now(), -24 * days))
        with app.app_context():
            removed = RequestRepository(get_db()).cleanup(before)
        click.echo(f"已清理 {removed} 条请求记录")
