"""操作日志仓储（只读查询 + 写入）。"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any

from ..domain.models import OperationLog
from ..utils import fmt, now
from .base import execute, fetch_all, fetch_one

LOG_SELECT = """
SELECT l.*,
       COALESCE(u.nickname, u.username) AS operator_name,
       CASE l.target_type
            WHEN 'ITEM' THEN (SELECT title FROM item WHERE item_id = l.target_id)
            WHEN 'RESERVATION' THEN (
                SELECT i.title FROM reservation r
                  JOIN item i ON i.item_id = r.item_id
                 WHERE r.reservation_id = l.target_id
            )
       END AS item_title
  FROM operation_log l
  LEFT JOIN user u ON u.user_id = l.operator_id
"""


class LogAction:
    ITEM_CREATE = "ITEM_CREATE"
    ITEM_UPDATE = "ITEM_UPDATE"
    ITEM_SUBMIT = "ITEM_SUBMIT"
    ITEM_APPROVE = "ITEM_APPROVE"
    ITEM_REJECT = "ITEM_REJECT"
    ITEM_DELIST = "ITEM_DELIST"
    ITEM_VIOLATION = "ITEM_VIOLATION"
    RESERVATION_CREATE = "RESERVATION_CREATE"
    RESERVATION_CANCEL = "RESERVATION_CANCEL"
    RESERVATION_REJECT = "RESERVATION_REJECT"
    RESERVATION_CONFIRM = "RESERVATION_CONFIRM"
    RESERVATION_COMPLETE = "RESERVATION_COMPLETE"
    RESERVATION_EXPIRE = "RESERVATION_EXPIRE"


LOG_ACTION_LABELS = {
    LogAction.ITEM_CREATE: "创建商品",
    LogAction.ITEM_UPDATE: "修改商品",
    LogAction.ITEM_SUBMIT: "提交审核",
    LogAction.ITEM_APPROVE: "审核通过",
    LogAction.ITEM_REJECT: "审核驳回",
    LogAction.ITEM_DELIST: "卖家下架",
    LogAction.ITEM_VIOLATION: "违规下架",
    LogAction.RESERVATION_CREATE: "创建预约",
    LogAction.RESERVATION_CANCEL: "取消预约",
    LogAction.RESERVATION_REJECT: "拒绝预约",
    LogAction.RESERVATION_CONFIRM: "确认预约",
    LogAction.RESERVATION_COMPLETE: "交易完成",
    LogAction.RESERVATION_EXPIRE: "预约过期",
}


@dataclass
class LogFilters:
    operator_id: int | None = None
    target_type: str | None = None
    target_id: int | None = None
    action: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    seller_id: int | None = None


class LogRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def insert(self, *, operator_id: int | None, operator_type: str,
               target_type: str, target_id: int, action: str,
               result: str = "SUCCESS", detail: str | None = None) -> int:
        cursor = execute(
            self.connection,
            """
            INSERT INTO operation_log (operator_id, operator_type, target_type,
                                       target_id, action, result, detail, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (operator_id, operator_type, target_type, target_id, action,
             result, detail, fmt(now())),
        )
        return int(cursor.lastrowid)

    def _where(self, filters: LogFilters) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if filters.operator_id is not None:
            clauses.append("l.operator_id = ?")
            params.append(filters.operator_id)
        if filters.target_type:
            clauses.append("l.target_type = ?")
            params.append(filters.target_type)
        if filters.target_id is not None:
            clauses.append("l.target_id = ?")
            params.append(filters.target_id)
        if filters.action:
            clauses.append("l.action = ?")
            params.append(filters.action)
        if filters.date_from:
            clauses.append("l.created_at >= ?")
            params.append(filters.date_from)
        if filters.date_to:
            clauses.append("l.created_at <= ?")
            params.append(filters.date_to + " 23:59:59.999")
        if filters.seller_id is not None:
            clauses.append(
                """(
                    (l.target_type = 'ITEM' AND EXISTS (
                        SELECT 1 FROM item i WHERE i.item_id = l.target_id AND i.seller_id = ?
                    ))
                    OR
                    (l.target_type = 'RESERVATION' AND EXISTS (
                        SELECT 1 FROM reservation r JOIN item i ON i.item_id = r.item_id
                         WHERE r.reservation_id = l.target_id AND i.seller_id = ?
                    ))
                )"""
            )
            params.extend([filters.seller_id, filters.seller_id])
        if not clauses:
            return "", []
        return " WHERE " + " AND ".join(clauses), params

    def query(self, filters: LogFilters, limit: int, offset: int) -> list[OperationLog]:
        where, params = self._where(filters)
        sql = LOG_SELECT + where + " ORDER BY l.created_at DESC, l.log_id DESC LIMIT ? OFFSET ?"
        rows = fetch_all(self.connection, sql, [*params, limit, offset])
        return [OperationLog.from_row(row) for row in rows]

    def count(self, filters: LogFilters) -> int:
        where, params = self._where(filters)
        row = fetch_one(
            self.connection, "SELECT COUNT(*) AS total FROM operation_log l" + where, params
        )
        return int(row["total"]) if row else 0

    def count_action(self, action: str) -> int:
        row = fetch_one(
            self.connection,
            "SELECT COUNT(*) AS total FROM operation_log WHERE action = ?",
            (action,),
        )
        return int(row["total"]) if row else 0
