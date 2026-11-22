"""Web 层公共函数。"""

from __future__ import annotations

from flask import current_app, request

from ..domain.enums import ItemStatus
from ..repositories.log_repo import LogFilters
from ..services.dto import ItemInput
from ..utils import Page, parse_page


def get_page() -> Page:
    return parse_page(
        request.args.get("page"),
        request.args.get("page_size"),
        default_size=current_app.config["PER_PAGE"],
        max_size=current_app.config["MAX_PAGE_SIZE"],
    )


def form_page() -> Page:
    """POST 表单提交后返回列表时使用，页码从隐藏字段读取。"""

    return parse_page(
        request.form.get("page") or 1,
        current_app.config["PER_PAGE"],
        default_size=current_app.config["PER_PAGE"],
        max_size=current_app.config["MAX_PAGE_SIZE"],
    )


def item_input_from_form() -> ItemInput:
    form = request.form
    return ItemInput(
        title=form.get("title", ""),
        description=form.get("description", ""),
        category_id=int(form.get("category_id") or 0),
        condition_id=int(form.get("condition_id") or 0),
        price=form.get("price", ""),
        image_url=form.get("image_url", ""),
    )


def version_from_form() -> int:
    try:
        return int(request.form.get("version", ""))
    except ValueError:
        return -1


def item_status_filter() -> str | None:
    raw = (request.args.get("status") or "").strip()
    if not raw:
        return None
    try:
        return ItemStatus(raw).value
    except ValueError:
        return None


def log_filters_from_args(*, seller_id: int | None = None) -> LogFilters:
    args = request.args

    def integer(name: str) -> int | None:
        raw = (args.get(name) or "").strip()
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            return None

    return LogFilters(
        operator_id=integer("operator_id"),
        target_type=(args.get("target_type") or "").strip() or None,
        target_id=integer("target_id"),
        action=(args.get("action") or "").strip() or None,
        date_from=(args.get("date_from") or "").strip() or None,
        date_to=(args.get("date_to") or "").strip() or None,
        seller_id=seller_id,
    )


def safe_next(target: str | None) -> str | None:
    if not target:
        return None
    if not target.startswith("/") or target.startswith("//"):
        return None
    return target
