"""通用工具：时间格式化、参数校验与分页。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from .domain.errors import ValidationError

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
PHONE_PATTERN = re.compile(r"^1\d{10}$")
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_\u4e00-\u9fa5]{3,32}$")
URL_PATTERN = re.compile(r"^https?://", re.IGNORECASE)


def now() -> datetime:
    """返回本地当前时间（精确到毫秒）。"""

    current = datetime.now()
    return current.replace(microsecond=current.microsecond // 1000 * 1000)


def fmt(value: datetime | None) -> str | None:
    """把 datetime 转成数据库使用的字符串。"""

    if value is None:
        return None
    return value.strftime(DATETIME_FORMAT)


def parse(value: str | None) -> datetime | None:
    """把数据库字符串转回 datetime。"""

    if not value:
        return None
    return datetime.strptime(value, DATETIME_FORMAT)


def hours_later(base: datetime, hours: int) -> datetime:
    return base + timedelta(hours=hours)


def seconds_later(base: datetime, seconds: int) -> datetime:
    return base + timedelta(seconds=seconds)


def human_time(value: str | None) -> str:
    """界面展示用：去掉毫秒。"""

    parsed = parse(value)
    if parsed is None:
        return "-"
    return parsed.strftime("%Y-%m-%d %H:%M")


def remaining_text(expire_at: str | None, current: datetime | None = None) -> str:
    """把到期时间显示为“剩余 x 小时 y 分”。"""

    parsed = parse(expire_at)
    if parsed is None:
        return "-"
    delta = parsed - (current or now())
    if delta.total_seconds() <= 0:
        return "已超时"
    minutes = int(delta.total_seconds() // 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"剩余 {hours} 小时 {minutes} 分"
    return f"剩余 {minutes} 分"


@dataclass
class Page:
    """分页参数与结果。"""

    page: int
    page_size: int
    total: int

    @property
    def pages(self) -> int:
        if self.page_size <= 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.pages

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def parse_page(raw_page: Any, raw_size: Any, default_size: int = 20,
               max_size: int = 100) -> Page:
    """校验页码与每页条数，非法值抛出 ValueError。"""

    try:
        page = int(raw_page or 1)
        page_size = int(raw_size or default_size)
    except (TypeError, ValueError) as exc:
        raise ValueError("分页参数必须为整数") from exc
    if page < 1:
        raise ValueError("页码必须大于等于 1")
    if page_size < 1 or page_size > max_size:
        raise ValueError(f"每页条数必须在 1 到 {max_size} 之间")
    return Page(page=page, page_size=page_size, total=0)


def text(value: Any, field: str, *, required: bool = True, max_len: int | None = None) -> str:
    """清理并校验文本字段。"""

    if value is None:
        value = ""
    cleaned = str(value).strip()
    if required and not cleaned:
        raise ValidationError(f"{field}不能为空")
    if max_len and len(cleaned) > max_len:
        raise ValidationError(f"{field}不能超过 {max_len} 个字符")
    return cleaned


def money(value: Any) -> float:
    """校验价格：必须是大于 0 的数值，最多两位小数。"""

    try:
        amount = round(float(value), 2)
    except (TypeError, ValueError) as exc:
        raise ValidationError("价格必须是数字") from exc
    if amount <= 0:
        raise ValidationError("价格必须大于 0")
    if amount > 9_999_999.99:
        raise ValidationError("价格超出允许范围")
    return amount
