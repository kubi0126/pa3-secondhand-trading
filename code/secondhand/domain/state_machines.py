"""商品与预约状态机（与实验二状态图一一对应）。"""

from __future__ import annotations

from .enums import ItemStatus, ReservationStatus
from .errors import StateConflict

# 商品 8 状态的允许转换。终态：SOLD / DELISTED / VIOLATION_DELISTED。
ITEM_TRANSITIONS: dict[ItemStatus, frozenset[ItemStatus]] = {
    ItemStatus.DRAFT: frozenset({ItemStatus.PENDING_REVIEW}),
    ItemStatus.PENDING_REVIEW: frozenset({ItemStatus.PUBLISHED, ItemStatus.REJECTED}),
    ItemStatus.REJECTED: frozenset({ItemStatus.PENDING_REVIEW}),
    ItemStatus.PUBLISHED: frozenset({
        ItemStatus.PENDING_REVIEW,
        ItemStatus.RESERVED,
        ItemStatus.DELISTED,
        ItemStatus.VIOLATION_DELISTED,
    }),
    ItemStatus.RESERVED: frozenset({
        ItemStatus.PUBLISHED,
        ItemStatus.SOLD,
        ItemStatus.VIOLATION_DELISTED,
    }),
    ItemStatus.SOLD: frozenset(),
    ItemStatus.DELISTED: frozenset(),
    ItemStatus.VIOLATION_DELISTED: frozenset(),
}

# 预约 6 状态的允许转换。终态：CANCELLED / REJECTED / EXPIRED / COMPLETED。
RESERVATION_TRANSITIONS: dict[ReservationStatus, frozenset[ReservationStatus]] = {
    ReservationStatus.PENDING_CONFIRM: frozenset({
        ReservationStatus.CONFIRMED,
        ReservationStatus.CANCELLED,
        ReservationStatus.REJECTED,
        ReservationStatus.EXPIRED,
    }),
    ReservationStatus.CONFIRMED: frozenset({
        ReservationStatus.COMPLETED,
        ReservationStatus.CANCELLED,
        ReservationStatus.EXPIRED,
    }),
    ReservationStatus.CANCELLED: frozenset(),
    ReservationStatus.REJECTED: frozenset(),
    ReservationStatus.EXPIRED: frozenset(),
    ReservationStatus.COMPLETED: frozenset(),
}


def can_item_transition(current: ItemStatus, target: ItemStatus) -> bool:
    return target in ITEM_TRANSITIONS[current]


def assert_item_transition(current: ItemStatus, target: ItemStatus) -> None:
    if not can_item_transition(current, target):
        raise StateConflict(
            f"商品状态不允许从“{current.label}”变为“{target.label}”，请刷新后重试"
        )


def can_reservation_transition(current: ReservationStatus,
                               target: ReservationStatus) -> bool:
    return target in RESERVATION_TRANSITIONS[current]


def assert_reservation_transition(current: ReservationStatus,
                                   target: ReservationStatus) -> None:
    if not can_reservation_transition(current, target):
        raise StateConflict(
            f"预约状态不允许从“{current.label}”变为“{target.label}”，请刷新后重试"
        )


def item_next_statuses(current: ItemStatus) -> list[ItemStatus]:
    """按固定顺序返回可选状态，便于界面展示。"""

    order = list(ItemStatus)
    return [status for status in order if can_item_transition(current, status)]


def reservation_next_statuses(current: ReservationStatus) -> list[ReservationStatus]:
    order = list(ReservationStatus)
    return [status for status in order if can_reservation_transition(current, status)]
