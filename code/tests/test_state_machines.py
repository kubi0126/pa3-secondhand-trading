"""状态机单元测试：全枚举同状态之间的有序对，不做抽样。"""

from __future__ import annotations

import pytest

from secondhand.domain.enums import ItemStatus, ReservationStatus
from secondhand.domain.errors import StateConflict
from secondhand.domain.state_machines import (
    ITEM_TRANSITIONS,
    RESERVATION_TRANSITIONS,
    assert_item_transition,
    assert_reservation_transition,
    can_item_transition,
    can_reservation_transition,
)

ITEM_PAIRS = [
    (current, target)
    for current in ItemStatus
    for target in ItemStatus
    if current is not target
]
RESERVATION_PAIRS = [
    (current, target)
    for current in ReservationStatus
    for target in ReservationStatus
    if current is not target
]


@pytest.mark.parametrize(("current", "target"), ITEM_PAIRS)
def test_item_transition_matrix(current, target):
    """8 个状态两两组合，共 56 个有序对；允许则通过，禁止则抛冲突。"""
    allowed = target in ITEM_TRANSITIONS[current]
    assert can_item_transition(current, target) is allowed
    if allowed:
        assert_item_transition(current, target)
    else:
        with pytest.raises(StateConflict):
            assert_item_transition(current, target)


def test_item_transition_counts():
    legal = sum(len(targets) for targets in ITEM_TRANSITIONS.values())
    assert len(ITEM_PAIRS) == 56
    assert legal == 11
    assert len(ITEM_PAIRS) - legal == 45


@pytest.mark.parametrize(("current", "target"), RESERVATION_PAIRS)
def test_reservation_transition_matrix(current, target):
    """6 个状态两两组合，共 30 个有序对；允许则通过，禁止则抛冲突。"""
    allowed = target in RESERVATION_TRANSITIONS[current]
    assert can_reservation_transition(current, target) is allowed
    if allowed:
        assert_reservation_transition(current, target)
    else:
        with pytest.raises(StateConflict):
            assert_reservation_transition(current, target)


def test_reservation_transition_counts():
    legal = sum(len(targets) for targets in RESERVATION_TRANSITIONS.values())
    assert len(RESERVATION_PAIRS) == 30
    assert legal == 7
    assert len(RESERVATION_PAIRS) - legal == 23
