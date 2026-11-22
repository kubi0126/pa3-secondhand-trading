"""并发预约测试：先到先得与唯一有效预约。"""

from __future__ import annotations

import threading

from secondhand.db import get_db
from secondhand.domain.errors import AppError
from secondhand.repositories.item_repo import ItemRepository
from secondhand.repositories.reservation_repo import ReservationRepository
from secondhand.services.reservation_service import ReservationService


def test_two_buyers_only_one_wins(app, alice_id, bob_id, carol_id, make_published_item):
    item_id = make_published_item(alice_id, "并发预约")
    item = None
    with app.app_context():
        item = ItemRepository(get_db()).find_by_id(item_id)
    results: list[tuple[str, object]] = []
    lock = threading.Lock()

    def worker(user_id: int, request_id: str) -> None:
        with app.app_context():
            try:
                reservation_id = ReservationService(get_db()).create(
                    user_id, item_id, request_id, item.version
                )
                with lock:
                    results.append(("ok", reservation_id))
            except AppError as exc:
                with lock:
                    results.append((type(exc).__name__, exc.message))

    threads = [
        threading.Thread(target=worker, args=(bob_id, "concurrent-a")),
        threading.Thread(target=worker, args=(carol_id, "concurrent-b")),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    successes = [row for row in results if row[0] == "ok"]
    assert len(successes) == 1, results
    with app.app_context():
        db = get_db()
        active = ReservationRepository(db).find_active_by_item(item_id)
        assert active is not None
        assert ItemRepository(db).find_by_id(item_id).status.value == "RESERVED"
        count = db.execute(
            "SELECT COUNT(*) AS total FROM reservation WHERE item_id = ? "
            "AND status IN ('PENDING_CONFIRM','CONFIRMED')",
            (item_id,),
        ).fetchone()["total"]
        assert count == 1


def test_same_request_concurrent_returns_single_record(app, alice_id, bob_id,
                                                       make_published_item):
    item_id = make_published_item(alice_id, "并发幂等")
    with app.app_context():
        item = ItemRepository(get_db()).find_by_id(item_id)
    results: list[object] = []
    lock = threading.Lock()

    def worker() -> None:
        with app.app_context():
            try:
                reservation_id = ReservationService(get_db()).create(
                    bob_id, item_id, "same-concurrent-request", item.version
                )
                with lock:
                    results.append(reservation_id)
            except AppError as exc:
                with lock:
                    results.append(type(exc).__name__)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    with app.app_context():
        db = get_db()
        count = db.execute(
            "SELECT COUNT(*) AS total FROM reservation WHERE item_id = ? "
            "AND request_id = ?",
            (item_id, "same-concurrent-request"),
        ).fetchone()["total"]
        assert count == 1
