"""统计服务（REQ-015）。"""

from __future__ import annotations

import sqlite3
from typing import Any

from ..repositories.item_repo import ItemRepository
from ..repositories.reservation_repo import ReservationRepository
from ..repositories.user_repo import UserRepository


class StatService:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def admin_overview(self) -> dict[str, Any]:
        item_repo = ItemRepository(self.connection)
        reservation_repo = ReservationRepository(self.connection)
        users = UserRepository(self.connection).list_all()
        categories = item_repo.count_by_category()
        totals = {
            "users": len(users),
            "normal_users": sum(1 for user in users if user.role.value == "USER"),
            "admins": sum(1 for user in users if user.role.value == "ADMIN"),
            "published": sum(row["published"] for row in categories),
            "reserved": sum(row["reserved"] for row in categories),
            "sold": sum(row["sold"] for row in categories),
            "total_items": sum(row["total"] for row in categories),
            "pending_review": item_repo.count_pending_review(),
        }
        totals["active_reservations"] = reservation_repo.count_active()
        return {"totals": totals, "categories": categories}

    def seller_overview(self, seller_id: int) -> dict[str, Any]:
        item_repo = ItemRepository(self.connection)
        reservation_repo = ReservationRepository(self.connection)
        counts = item_repo.count_by_status_for_seller(seller_id)
        return {
            "published": counts.get("PUBLISHED", 0),
            "reserved": counts.get("RESERVED", 0),
            "sold": counts.get("SOLD", 0),
            "draft": counts.get("DRAFT", 0),
            "pending_review": counts.get("PENDING_REVIEW", 0),
            "rejected": counts.get("REJECTED", 0),
            "active_reservations": reservation_repo.count_active_by_seller(seller_id),
            "pending_confirm": reservation_repo.count_pending_by_seller(seller_id),
        }

    def buyer_overview(self, buyer_id: int) -> dict[str, int]:
        repo = ReservationRepository(self.connection)
        pending = repo.count_by_buyer(buyer_id, "PENDING_CONFIRM")
        confirmed = repo.count_by_buyer(buyer_id, "CONFIRMED")
        return {
            "pending": pending,
            "confirmed": confirmed,
            "active": pending + confirmed,
            "completed": repo.count_by_buyer(buyer_id, "COMPLETED"),
        }
