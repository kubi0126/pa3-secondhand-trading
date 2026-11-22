"""日志查询服务（REQ-016）。"""

from __future__ import annotations

import sqlite3

from ..repositories.log_repo import (
    LOG_ACTION_LABELS,
    LogAction,
    LogFilters,
    LogRepository,
)
from ..utils import Page


class LogService:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def query(self, filters: LogFilters, page: Page):
        repo = LogRepository(self.connection)
        page.total = repo.count(filters)
        return repo.query(filters, page.page_size, page.offset)

    def actions(self) -> list[tuple[str, str]]:
        return [
            (action, LOG_ACTION_LABELS[action])
            for action in (
                LogAction.ITEM_CREATE,
                LogAction.ITEM_UPDATE,
                LogAction.ITEM_SUBMIT,
                LogAction.ITEM_APPROVE,
                LogAction.ITEM_REJECT,
                LogAction.ITEM_DELIST,
                LogAction.ITEM_VIOLATION,
                LogAction.RESERVATION_CREATE,
                LogAction.RESERVATION_CANCEL,
                LogAction.RESERVATION_REJECT,
                LogAction.RESERVATION_CONFIRM,
                LogAction.RESERVATION_COMPLETE,
                LogAction.RESERVATION_EXPIRE,
            )
        ]
