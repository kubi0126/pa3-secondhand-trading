"""演示数据初始化（幂等）。"""

from __future__ import annotations

import sqlite3

from .services.security import hash_password
from .utils import fmt, hours_later, now


def _user(connection: sqlite3.Connection, username: str, phone: str,
          password: str, nickname: str, role: str = "USER") -> int:
    row = connection.execute(
        "SELECT user_id FROM user WHERE username = ?", (username,)
    ).fetchone()
    if row:
        return int(row["user_id"])
    cursor = connection.execute(
        """
        INSERT INTO user (username, phone, password_hash, nickname, role)
        VALUES (?, ?, ?, ?, ?)
        """,
        (username, phone, hash_password(password), nickname, role),
    )
    return int(cursor.lastrowid)


def _item(connection: sqlite3.Connection, seller_id: int, category_id: int,
          condition_id: int, title: str, description: str, price: float,
          status: str, image_url: str | None = None) -> int:
    timestamp = fmt(now())
    published_at = timestamp if status not in {"DRAFT", "PENDING_REVIEW", "REJECTED"} else None
    cursor = connection.execute(
        """
        INSERT INTO item (seller_id, category_id, condition_id, title, description,
                          price, image_url, status, version, published_at,
                          created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
        """,
        (seller_id, category_id, condition_id, title, description, price,
         image_url, status, published_at, timestamp, timestamp),
    )
    return int(cursor.lastrowid)


def seed_database(connection: sqlite3.Connection) -> None:
    """写入字典、演示账号与示例商品；已有数据时不重复写商品。"""

    categories = [
        ("教材", 10), ("数码", 20), ("生活用品", 30), ("运动户外", 40), ("其他", 50),
    ]
    for name, order in categories:
        connection.execute(
            "INSERT OR IGNORE INTO category (name, sort_order, enabled) VALUES (?, ?, 1)",
            (name, order),
        )
    conditions = [
        ("全新", 10), ("九五新", 20), ("九成新", 30), ("八成新", 40), ("七成新及以下", 50),
    ]
    for name, order in conditions:
        connection.execute(
            "INSERT OR IGNORE INTO item_condition (name, sort_order, enabled) VALUES (?, ?, 1)",
            (name, order),
        )

    admin_id = _user(connection, "admin", "13800000000", "Admin@123", "平台管理员", "ADMIN")
    alice_id = _user(connection, "alice", "13800000001", "User@123", "林同学")
    bob_id = _user(connection, "bob", "13800000002", "User@123", "周同学")
    _user(connection, "carol", "13800000003", "User@123", "陈同学")

    existing = connection.execute("SELECT COUNT(*) AS total FROM item").fetchone()["total"]
    if existing:
        return

    category_ids = {
        row["name"]: row["category_id"]
        for row in connection.execute("SELECT category_id, name FROM category")
    }
    condition_ids = {
        row["name"]: row["condition_id"]
        for row in connection.execute("SELECT condition_id, name FROM item_condition")
    }

    item_ids: dict[str, int] = {}
    item_ids["高数教材"] = _item(
        connection, alice_id, category_ids["教材"], condition_ids["八成新"],
        "高等数学 同济第七版 上下册",
        "课上用过一学期，笔记较少，无缺页。适合大一预习和期末复习。",
        28.0, "PUBLISHED",
    )
    item_ids["iPad"] = _item(
        connection, alice_id, category_ids["数码"], condition_ids["九五新"],
        "iPad 第 9 代 64G 深空灰",
        "2024 年购入，电池健康 92%，附原装充电器与保护壳。",
        1350.0, "PUBLISHED",
    )
    item_ids["台灯"] = _item(
        connection, alice_id, category_ids["生活用品"], condition_ids["九成新"],
        "米家 LED 台灯 Pro",
        "毕业搬宿舍出，护眼模式正常，无划痕。",
        95.0, "PUBLISHED",
    )
    item_ids["羽毛球拍"] = _item(
        connection, alice_id, category_ids["运动户外"], condition_ids["九成新"],
        "尤尼克斯羽毛球拍 双拍套装",
        "含拍套与三只训练球，适合入门。",
        120.0, "PUBLISHED",
    )
    item_ids["显示器"] = _item(
        connection, alice_id, category_ids["数码"], condition_ids["八成新"],
        "戴尔 24 寸 IPS 显示器",
        "1080P，HDMI 接口，宿舍桌面使用，无坏点。",
        430.0, "PUBLISHED",
    )
    item_ids["待审核"] = _item(
        connection, alice_id, category_ids["其他"], condition_ids["全新"],
        "全新未拆封机械键盘",
        "青轴 87 键，朋友送的，用不上。",
        199.0, "PENDING_REVIEW",
    )
    item_ids["草稿"] = _item(
        connection, alice_id, category_ids["教材"], condition_ids["七成新及以下"],
        "线性代数辅导讲义（草稿）",
        "还在整理照片，稍后补充。",
        15.0, "DRAFT",
    )
    item_ids["已预约"] = _item(
        connection, alice_id, category_ids["数码"], condition_ids["九五新"],
        "索尼 WH-1000XM4 头戴耳机",
        "降噪正常，耳罩无脱皮，附收纳包。",
        880.0, "RESERVED",
    )
    item_ids["已售出"] = _item(
        connection, alice_id, category_ids["生活用品"], condition_ids["八成新"],
        "宿舍折叠小书桌",
        "已线下交易完成。",
        45.0, "SOLD",
    )

    # 待确认预约：商品 RESERVED
    expire_at = fmt(hours_later(now(), 20))
    cursor = connection.execute(
        """
        INSERT INTO reservation (item_id, buyer_id, status, version, request_id,
                                 created_at, expire_at)
        VALUES (?, ?, 'PENDING_CONFIRM', 0, ?, ?, ?)
        """,
        (item_ids["已预约"], bob_id, "seed-reservation-1", fmt(now()), expire_at),
    )
    reservation_id = int(cursor.lastrowid)
    connection.execute(
        """
        INSERT INTO operation_log (operator_id, operator_type, target_type, target_id,
                                   action, result, detail, created_at)
        VALUES (?, 'USER', 'RESERVATION', ?, 'RESERVATION_CREATE', 'SUCCESS', ?, ?)
        """,
        (bob_id, reservation_id, "演示数据：预约耳机", fmt(now())),
    )

    # 已完成预约：商品 SOLD
    completed_at = fmt(hours_later(now(), -30))
    cursor = connection.execute(
        """
        INSERT INTO reservation (item_id, buyer_id, status, version, request_id,
                                 created_at, confirmed_at, completed_at, expire_at)
        VALUES (?, ?, 'COMPLETED', 0, ?, ?, ?, ?, ?)
        """,
        (item_ids["已售出"], bob_id, "seed-reservation-2",
         fmt(hours_later(now(), -50)), fmt(hours_later(now(), -48)),
         completed_at, fmt(hours_later(now(), -2))),
    )
    reservation_id = int(cursor.lastrowid)
    connection.execute(
        """
        INSERT INTO operation_log (operator_id, operator_type, target_type, target_id,
                                   action, result, detail, created_at)
        VALUES (?, 'USER', 'RESERVATION', ?, 'RESERVATION_COMPLETE', 'SUCCESS', ?, ?)
        """,
        (alice_id, reservation_id, "演示数据：折叠桌交易完成", completed_at),
    )
    connection.execute(
        """
        INSERT INTO operation_log (operator_id, operator_type, target_type, target_id,
                                   action, result, detail, created_at)
        VALUES (?, 'USER', 'ITEM', ?, 'ITEM_APPROVE', 'SUCCESS', ?, ?)
        """,
        (admin_id, item_ids["iPad"], "演示数据：审核通过", fmt(hours_later(now(), -72))),
    )
