"""商品浏览、发布、编辑、预约入口。"""

from __future__ import annotations

import uuid

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from ..db import get_db
from ..domain.enums import ItemStatus, Role
from ..domain.errors import AppError, PermissionDenied
from ..repositories.dict_repo import DictionaryRepository
from ..repositories.item_repo import ItemRepository
from ..services.item_service import ItemService
from ..services.query_service import QueryService
from ..services.reservation_service import ReservationService
from .auth import current_user, login_required, seller_required
from .helpers import get_page, item_input_from_form, version_from_form

items_bp = Blueprint("items", __name__)


def _form_options() -> dict:
    repo = DictionaryRepository(get_db())
    return {
        "categories": repo.list_categories(enabled_only=True),
        "conditions": repo.list_conditions(enabled_only=True),
    }


@items_bp.route("/")
def index():
    try:
        result = QueryService(
            get_db(),
            default_page_size=current_app.config["PER_PAGE"],
            max_page_size=current_app.config["MAX_PAGE_SIZE"],
        ).browse(request.args.to_dict())
    except (ValueError, AppError) as exc:
        flash(str(exc), "error")
        return redirect(url_for("items.index"))
    return render_template("items/list.html", **result)


@items_bp.route("/items/<int:item_id>")
def detail(item_id: int):
    viewer = current_user()
    data = ItemService(get_db()).get_detail(item_id, viewer)
    item = data["item"]
    can_reserve = (
        viewer is not None
        and viewer.role is Role.USER
        and viewer.user_id != item.seller_id
        and item.status is ItemStatus.PUBLISHED
    )
    return render_template(
        "items/detail.html",
        item=item,
        audits=data["audits"],
        active_reservation=data["active_reservation"],
        can_reserve=can_reserve,
        request_id=uuid.uuid4().hex,
    )


@items_bp.route("/items/new", methods=["GET", "POST"])
@seller_required
def new():
    if request.method == "POST":
        service = ItemService(get_db())
        try:
            item_id = service.create_draft(current_user().user_id, item_input_from_form())
            if request.form.get("action") == "submit":
                item = ItemRepository(get_db()).find_by_id(item_id)
                service.submit(current_user().user_id, item_id, item.version)
                flash("商品已提交审核", "success")
            else:
                flash("草稿已保存", "success")
            return redirect(url_for("seller.my_items"))
        except AppError as exc:
            flash(exc.message, "error")
            return render_template(
                "items/form.html",
                item=None,
                form=request.form,
                action="new",
                ** _form_options(),
            ), exc.status_code
    return render_template(
        "items/form.html", item=None, form={}, action="new", **_form_options()
    )


@items_bp.route("/items/<int:item_id>/edit", methods=["GET", "POST"])
@seller_required
def edit(item_id: int):
    service = ItemService(get_db())
    item = service.get_detail(item_id, current_user())["item"]
    if item.seller_id != current_user().user_id:
        raise PermissionDenied("只能编辑自己的商品")
    if item.status not in {ItemStatus.DRAFT, ItemStatus.REJECTED, ItemStatus.PUBLISHED}:
        flash(f"商品当前为“{item.status.label}”，不能编辑", "error")
        return redirect(url_for("seller.my_items"))

    if request.method == "POST":
        try:
            new_status = service.update(
                current_user().user_id, item_id, item_input_from_form(),
                version_from_form(),
            )
            if request.form.get("action") == "submit" and new_status is not ItemStatus.PENDING_REVIEW:
                refreshed = ItemRepository(get_db()).find_by_id(item_id)
                service.submit(current_user().user_id, item_id, refreshed.version)
                flash("商品已提交审核", "success")
            else:
                flash("商品已保存", "success")
            return redirect(url_for("seller.my_items"))
        except AppError as exc:
            flash(exc.message, "error")
            refreshed = ItemRepository(get_db()).find_by_id(item_id)
            return render_template(
                "items/form.html",
                item=refreshed,
                form=request.form,
                action="edit",
                **_form_options(),
            ), exc.status_code

    return render_template(
        "items/form.html", item=item, form={}, action="edit", **_form_options()
    )


@items_bp.route("/items/<int:item_id>/submit", methods=["POST"])
@seller_required
def submit(item_id: int):
    try:
        ItemService(get_db()).submit(current_user().user_id, item_id, version_from_form())
        flash("已提交审核，等待管理员处理", "success")
    except AppError as exc:
        flash(exc.message, "error")
    return redirect(url_for("seller.my_items"))


@items_bp.route("/items/<int:item_id>/delist", methods=["POST"])
@seller_required
def delist(item_id: int):
    try:
        ItemService(get_db()).delist(current_user().user_id, item_id, version_from_form())
        flash("商品已下架", "success")
    except AppError as exc:
        flash(exc.message, "error")
    return redirect(url_for("seller.my_items"))


@items_bp.route("/items/<int:item_id>/reserve", methods=["POST"])
@login_required
def reserve(item_id: int):
    user = current_user()
    if user.role is not Role.USER:
        flash("管理员不参与购买", "error")
        return redirect(url_for("items.detail", item_id=item_id))
    try:
        reservation_id = ReservationService(
            get_db(),
            confirm_hours=current_app.config["RESERVATION_CONFIRM_HOURS"],
            complete_hours=current_app.config["RESERVATION_COMPLETE_HOURS"],
            duplicate_seconds=current_app.config["DUPLICATE_RESERVATION_SECONDS"],
        ).create(
            user.user_id,
            item_id,
            request.form.get("request_id", ""),
            version_from_form(),
        )
        flash("预约已创建，等待卖家确认", "success")
        return redirect(url_for("buyer.my_reservations", highlight=reservation_id))
    except AppError as exc:
        flash(exc.message, "error")
        return redirect(url_for("items.detail", item_id=item_id))
