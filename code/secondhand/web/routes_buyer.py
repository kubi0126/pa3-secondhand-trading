"""买家：我的预约与取消。"""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..db import get_db
from ..domain.errors import AppError, NotFound
from ..services.reservation_service import ReservationService
from ..services.stat_service import StatService
from .auth import current_user, login_required
from .helpers import get_page, version_from_form

buyer_bp = Blueprint("buyer", __name__)


@buyer_bp.route("/my/reservations")
@login_required
def my_reservations():
    status = (request.args.get("status") or "").strip() or None
    try:
        page = get_page()
        reservations = ReservationService(get_db()).list_my(
            current_user().user_id, status, page
        )
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("buyer.my_reservations"))
    except AppError as exc:
        flash(exc.message, "error")
        return redirect(url_for("buyer.my_reservations"))

    return render_template(
        "buyer/reservations.html",
        reservations=reservations,
        page=page,
        status=status,
        highlight=request.args.get("highlight", type=int),
        stats=StatService(get_db()).buyer_overview(current_user().user_id),
    )


@buyer_bp.route("/reservations/<int:reservation_id>/cancel", methods=["POST"])
@login_required
def cancel(reservation_id: int):
    try:
        ReservationService(get_db()).cancel(
            current_user().user_id, reservation_id, version_from_form()
        )
        flash("预约已取消，商品恢复在售", "success")
    except NotFound:
        flash("预约不存在", "error")
    except AppError as exc:
        flash(exc.message, "error")
    return redirect(url_for("buyer.my_reservations"))
