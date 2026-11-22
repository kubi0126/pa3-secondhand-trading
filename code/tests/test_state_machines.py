"""状态机单元测试：覆盖允许与禁止转换。"""

from __future__ import annotations

import pytest

from secondhand.domain.enums import ItemStatus, ReservationStatus
from secondhand.domain.errors import StateConflict
from secondhand.domain.state_machines import (
    assert_item_transition,
    assert_reservation_transition,
    can_item_transition,
    can_reservation_transition,
)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (ItemStatus.DRAFT, ItemStatus.PENDING_REVIEW),
        (ItemStatus.PENDING_REVIEW, ItemStatus.PUBLISHED),
        (ItemStatus.PENDING_REVIEW, ItemStatus.REJECTED),
        (ItemStatus.REJECTED, ItemStatus.PENDING_REVIEW),
        (ItemStatus.PUBLISHED, ItemStatus.PENDING_REVIEW),
        (ItemStatus.PUBLISHED, ItemStatus.RESERVED),
        (ItemStatus.PUBLISHED, ItemStatus.DELISTED),
        (ItemStatus.PUBLISHED, ItemStatus.VIOLATION_DELISTED),
        (ItemStatus.RESERVED, ItemStatus.PUBLISHED),
        (ItemStatus.RESERVED, ItemStatus.SOLD),
        (ItemStatus.RESERVED, ItemStatus.VIOLATION_DELISTED),
    ],
)
def test_item_allowed_transitions(current, target):
    assert can_item_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (ItemStatus.DRAFT, ItemStatus.PUBLISHED),
        (ItemStatus.DRAFT, ItemStatus.RESERVED),
        (ItemStatus.SOLD, ItemStatus.PUBLISHED),
        (ItemStatus.DELISTED, ItemStatus.PUBLISHED),
        (ItemStatus.VIOLATION_DELISTED, ItemStatus.PUBLISHED),
        (ItemStatus.RESERVED, ItemStatus.DELISTED),
        (ItemStatus.PUBLISHED, ItemStatus.SOLD),
    ],
)
def test_item_forbidden_transitions(current, target):
    assert not can_item_transition(current, target)
    with pytest.raises(StateConflict):
        assert_item_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (ReservationStatus.PENDING_CONFIRM, ReservationStatus.CONFIRMED),
        (ReservationStatus.PENDING_CONFIRM, ReservationStatus.CANCELLED),
        (ReservationStatus.PENDING_CONFIRM, ReservationStatus.REJECTED),
        (ReservationStatus.PENDING_CONFIRM, ReservationStatus.EXPIRED),
        (ReservationStatus.CONFIRMED, ReservationStatus.COMPLETED),
        (ReservationStatus.CONFIRMED, ReservationStatus.CANCELLED),
        (ReservationStatus.CONFIRMED, ReservationStatus.EXPIRED),
    ],
)
def test_reservation_allowed_transitions(current, target):
    assert can_reservation_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (ReservationStatus.PENDING_CONFIRM, ReservationStatus.COMPLETED),
        (ReservationStatus.COMPLETED, ReservationStatus.CANCELLED),
        (ReservationStatus.CANCELLED, ReservationStatus.CONFIRMED),
        (ReservationStatus.EXPIRED, ReservationStatus.CONFIRMED),
    ],
)
def test_reservation_forbidden_transitions(current, target):
    assert not can_reservation_transition(current, target)
    with pytest.raises(StateConflict):
        assert_reservation_transition(current, target)
