"""服务层输入对象。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ItemInput:
    title: str
    description: str
    category_id: int
    condition_id: int
    price: str | float
    image_url: str
