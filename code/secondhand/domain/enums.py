"""领域枚举与中文文案。"""

from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"

    @property
    def label(self) -> str:
        return {"USER": "普通用户", "ADMIN": "管理员"}[self.value]


class ItemStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    PUBLISHED = "PUBLISHED"
    RESERVED = "RESERVED"
    SOLD = "SOLD"
    DELISTED = "DELISTED"
    REJECTED = "REJECTED"
    VIOLATION_DELISTED = "VIOLATION_DELISTED"

    @property
    def label(self) -> str:
        return ITEM_STATUS_LABELS[self.value]

    @property
    def css_class(self) -> str:
        return ITEM_STATUS_CSS[self.value]


ITEM_STATUS_LABELS = {
    "DRAFT": "草稿",
    "PENDING_REVIEW": "待审核",
    "PUBLISHED": "已发布",
    "RESERVED": "已预约",
    "SOLD": "已售出",
    "DELISTED": "已下架",
    "REJECTED": "审核驳回",
    "VIOLATION_DELISTED": "违规下架",
}

ITEM_STATUS_CSS = {
    "DRAFT": "badge-gray",
    "PENDING_REVIEW": "badge-warning",
    "PUBLISHED": "badge-success",
    "RESERVED": "badge-info",
    "SOLD": "badge-dark",
    "DELISTED": "badge-gray",
    "REJECTED": "badge-danger",
    "VIOLATION_DELISTED": "badge-danger",
}


class ReservationStatus(str, Enum):
    PENDING_CONFIRM = "PENDING_CONFIRM"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    COMPLETED = "COMPLETED"

    @property
    def label(self) -> str:
        return RESERVATION_STATUS_LABELS[self.value]

    @property
    def css_class(self) -> str:
        return RESERVATION_STATUS_CSS[self.value]


RESERVATION_STATUS_LABELS = {
    "PENDING_CONFIRM": "待确认",
    "CONFIRMED": "已确认",
    "CANCELLED": "已取消",
    "REJECTED": "已拒绝",
    "EXPIRED": "已过期",
    "COMPLETED": "已完成",
}

RESERVATION_STATUS_CSS = {
    "PENDING_CONFIRM": "badge-warning",
    "CONFIRMED": "badge-info",
    "CANCELLED": "badge-gray",
    "REJECTED": "badge-danger",
    "EXPIRED": "badge-gray",
    "COMPLETED": "badge-success",
}


class AuditResult(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

    @property
    def label(self) -> str:
        return {"APPROVED": "通过", "REJECTED": "驳回"}[self.value]


class OperatorType(str, Enum):
    USER = "USER"
    SYSTEM = "SYSTEM"


class RequestStatus(str, Enum):
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
