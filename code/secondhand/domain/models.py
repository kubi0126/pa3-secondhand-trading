"""领域实体（与实验二类图对应）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .enums import (
    AuditResult,
    ItemStatus,
    OperatorType,
    ReservationStatus,
    Role,
)


def _row_value(row: Mapping[str, Any], key: str, default: Any = None) -> Any:
    try:
        return row[key]
    except (IndexError, KeyError):
        return default


@dataclass
class User:
    user_id: int
    username: str
    phone: str
    password_hash: str
    nickname: str | None
    role: Role
    failed_attempts: int
    locked_until: str | None
    created_at: str
    updated_at: str

    @property
    def display_name(self) -> str:
        return self.nickname or self.username

    @property
    def is_admin(self) -> bool:
        return self.role is Role.ADMIN

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "User":
        return cls(
            user_id=row["user_id"],
            username=row["username"],
            phone=row["phone"],
            password_hash=row["password_hash"],
            nickname=row["nickname"],
            role=Role(row["role"]),
            failed_attempts=row["failed_attempts"],
            locked_until=row["locked_until"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


@dataclass
class Category:
    category_id: int
    name: str
    sort_order: int
    enabled: bool

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "Category":
        return cls(
            category_id=row["category_id"],
            name=row["name"],
            sort_order=row["sort_order"],
            enabled=bool(row["enabled"]),
        )


@dataclass
class ItemCondition:
    condition_id: int
    name: str
    sort_order: int
    enabled: bool

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "ItemCondition":
        return cls(
            condition_id=row["condition_id"],
            name=row["name"],
            sort_order=row["sort_order"],
            enabled=bool(row["enabled"]),
        )


@dataclass
class Item:
    item_id: int
    seller_id: int
    category_id: int
    condition_id: int
    title: str
    description: str | None
    price: float
    image_url: str | None
    status: ItemStatus
    version: int
    published_at: str | None
    created_at: str
    updated_at: str
    category_name: str | None = None
    condition_name: str | None = None
    seller_name: str | None = None

    @property
    def status_label(self) -> str:
        return self.status.label

    @property
    def is_public(self) -> bool:
        return self.status is ItemStatus.PUBLISHED

    @property
    def is_editable(self) -> bool:
        return self.status in {
            ItemStatus.DRAFT,
            ItemStatus.REJECTED,
            ItemStatus.PUBLISHED,
        }

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "Item":
        return cls(
            item_id=row["item_id"],
            seller_id=row["seller_id"],
            category_id=row["category_id"],
            condition_id=row["condition_id"],
            title=row["title"],
            description=_row_value(row, "description"),
            price=float(row["price"]),
            image_url=_row_value(row, "image_url"),
            status=ItemStatus(row["status"]),
            version=row["version"],
            published_at=_row_value(row, "published_at"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            category_name=_row_value(row, "category_name"),
            condition_name=_row_value(row, "condition_name"),
            seller_name=_row_value(row, "seller_name"),
        )


@dataclass
class Reservation:
    reservation_id: int
    item_id: int
    buyer_id: int
    status: ReservationStatus
    version: int
    request_id: str | None
    cancel_reason: str | None
    created_at: str
    confirmed_at: str | None
    completed_at: str | None
    expire_at: str
    item_title: str | None = None
    item_price: float | None = None
    item_status: str | None = None
    buyer_name: str | None = None
    seller_id: int | None = None
    seller_name: str | None = None

    @property
    def status_label(self) -> str:
        return self.status.label

    @property
    def is_active(self) -> bool:
        return self.status in {
            ReservationStatus.PENDING_CONFIRM,
            ReservationStatus.CONFIRMED,
        }

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "Reservation":
        return cls(
            reservation_id=row["reservation_id"],
            item_id=row["item_id"],
            buyer_id=row["buyer_id"],
            status=ReservationStatus(row["status"]),
            version=row["version"],
            request_id=_row_value(row, "request_id"),
            cancel_reason=_row_value(row, "cancel_reason"),
            created_at=row["created_at"],
            confirmed_at=_row_value(row, "confirmed_at"),
            completed_at=_row_value(row, "completed_at"),
            expire_at=row["expire_at"],
            item_title=_row_value(row, "item_title"),
            item_price=_row_value(row, "item_price"),
            item_status=_row_value(row, "item_status"),
            buyer_name=_row_value(row, "buyer_name"),
            seller_id=_row_value(row, "seller_id"),
            seller_name=_row_value(row, "seller_name"),
        )


@dataclass
class AuditRecord:
    audit_id: int
    item_id: int
    admin_id: int
    result: AuditResult
    reason: str | None
    created_at: str
    admin_name: str | None = None
    item_title: str | None = None

    @property
    def result_label(self) -> str:
        return self.result.label

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "AuditRecord":
        return cls(
            audit_id=row["audit_id"],
            item_id=row["item_id"],
            admin_id=row["admin_id"],
            result=AuditResult(row["result"]),
            reason=_row_value(row, "reason"),
            created_at=row["created_at"],
            admin_name=_row_value(row, "admin_name"),
            item_title=_row_value(row, "item_title"),
        )


@dataclass
class OperationLog:
    log_id: int
    operator_id: int | None
    operator_type: OperatorType
    target_type: str
    target_id: int
    action: str
    result: str
    detail: str | None
    created_at: str
    operator_name: str | None = None
    item_title: str | None = None

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "OperationLog":
        return cls(
            log_id=row["log_id"],
            operator_id=_row_value(row, "operator_id"),
            operator_type=OperatorType(row["operator_type"]),
            target_type=row["target_type"],
            target_id=row["target_id"],
            action=row["action"],
            result=row["result"],
            detail=_row_value(row, "detail"),
            created_at=row["created_at"],
            operator_name=_row_value(row, "operator_name"),
            item_title=_row_value(row, "item_title"),
        )


@dataclass
class RequestLog:
    request_id: str
    user_id: int
    endpoint: str
    status: str
    result_json: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "RequestLog":
        return cls(
            request_id=row["request_id"],
            user_id=row["user_id"],
            endpoint=row["endpoint"],
            status=row["status"],
            result_json=row["result_json"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
