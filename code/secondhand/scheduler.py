"""预约超时扫描后台线程。"""

from __future__ import annotations

import threading

from flask import Flask

from .db import get_db
from .services.reservation_service import ReservationService


def start_scheduler(app: Flask) -> threading.Event | None:
    """按固定间隔扫描超时预约；返回 stop event，便于测试或退出。"""

    if not app.config.get("SCHEDULER_ENABLED", False):
        return None

    stop = threading.Event()
    interval = int(app.config.get("SCHEDULER_INTERVAL_SECONDS", 60))

    def loop() -> None:
        while not stop.wait(interval):
            try:
                with app.app_context():
                    service = ReservationService(
                        get_db(),
                        confirm_hours=app.config["RESERVATION_CONFIRM_HOURS"],
                        complete_hours=app.config["RESERVATION_COMPLETE_HOURS"],
                        duplicate_seconds=app.config["DUPLICATE_RESERVATION_SECONDS"],
                    )
                    expired = service.expire_due()
                    if expired:
                        app.logger.info("expired %s reservations", expired)
            except Exception:  # pylint: disable=broad-exception-caught
                app.logger.exception("scheduler failed")

    thread = threading.Thread(target=loop, name="reservation-scheduler", daemon=True)
    thread.start()
    return stop
