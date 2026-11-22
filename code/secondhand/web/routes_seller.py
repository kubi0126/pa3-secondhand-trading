"""卖家：我的商品、待处理预约与商品日志。"""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..db import get_db
from ..domain.errors import AppError
from ..services.item_service import ItemService
from ..services.log_service import LogService
from ..services.reservation_service import ReservationService
from ..services.stat_service import StatService
from .auth import current_user, seller_required
from .helpers import (
    get_page,
    item_status_filter,
    log_filters_from_args,
    version_from_form,
)

seller_bp = Blueprint("seller", __name__)


@seller_bp.route("/my/items")
@seller_required
def my_items():
    status = item_status_filter()
    try:
        page = get_page()
        items = ItemService(get_db()).list_my(current_user().user_id, status, page)
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("seller.my_items"))
    return render_template(
        "seller/items.html",
        items=items,
        page=page,
        status=status,
        stats=ItemService(get_db()).seller_stats(current_user().user_id),
    )


@seller_bp.route("/seller/reservations")
@seller_required
def reservations():
    raw_status = (request.args.get("status") or "PENDING_CONFIRM").strip()
    status = None if raw_status == "ALL" else raw_status
    try:
        page = get_page()
        reservations = ReservationService(get_db()).list_seller(
            current_user().user_id, status, page
        )
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("seller.reservations"))
    except AppError as exc:
        flash(exc.message, "error")
        return redirect(url_for("seller.reservations"))
    return render_template(
        "seller/reservations.html",
        reservations=reservations,
        page=page,
        status=status,
        stats=StatService(get_db()).seller_overview(current_user().user_id),
    )


@seller_bp.route("/seller/reservations/<int:reservation_id>/confirm", methods=["POST"])
@seller_required
def confirm(reservation_id: int):
    try:
        ReservationService(get_db()).confirm(
            current_user().user_id, reservation_id, version_from_form()
        )
        flash("已确认预约，请在 48 小时内完成线下交易", "success")
    except AppError as exc:
        flash(exc.message, "error")
    return redirect(request.form.get("back") or url_for("seller.reservations"))


@seller_bp.route("/seller/reservations/<int:reservation_id>/reject", methods=["POST"])
@seller_required
def reject(reservation_id: int):
    try:
        ReservationService(get_db()).reject(
            current_user().user_id,
            reservation_id,
            request.form.get("reason", ""),
            version_from_form(),
        )
        flash("已拒绝预约，商品恢复在售", "success")
    except AppError as exc:
        flash(exc.message, "error")
    return redirect(request.form.get("back") or url_for("seller.reservations"))


@seller_bp.route("/seller/reservations/<int:reservation_id>/complete", methods=["POST"])
@seller_required
def complete(reservation_id: int):
    try:
        ReservationService(get_db()).complete(
            current_user().user_id, reservation_id, version_from_form()
        )
        flash("交易已完成，商品标记为已售出", "success")
    except AppError as exc:
        flash(exc.message, "error")
    return redirect(request.form.get("back") or url_for("seller.reservations"))


@seller_bp.route("/seller/logs")
@seller_required
def logs():
    try:
        page = get_page()
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("seller.logs"))
    filters = log_filters_from_args(seller_id=current_user().user_id)
    service = LogService(get_db())
    entries = service.query(filters, page)
    return render_template(
        "logs.html",
        logs=entries,
        page=page,
        actions=service.actions(),
        filters=request.args,
        scope="seller",
    )
