"""管理员：审核、违规下架、日志、统计与字典。"""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..db import get_db
from ..domain.errors import AppError
from ..services.audit_service import AuditService
from ..services.dict_service import DictService
from ..services.log_service import LogService
from ..services.stat_service import StatService
from .auth import admin_required, current_user
from .helpers import get_page, item_status_filter, log_filters_from_args

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("")
@admin_required
def home():
    return redirect(url_for("admin.review"))


@admin_bp.route("/review")
@admin_required
def review():
    try:
        page = get_page()
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("admin.review"))
    items = AuditService(get_db()).pending_list(page)
    return render_template("admin/review.html", items=items, page=page)


@admin_bp.route("/review/<int:item_id>/approve", methods=["POST"])
@admin_required
def approve(item_id: int):
    try:
        AuditService(get_db()).approve(
            _admin_id(), item_id, _version()
        )
        flash("审核通过，商品已发布", "success")
    except AppError as exc:
        flash(exc.message, "error")
    return redirect(url_for("admin.review"))


@admin_bp.route("/review/<int:item_id>/reject", methods=["POST"])
@admin_required
def reject(item_id: int):
    try:
        AuditService(get_db()).reject(
            _admin_id(), item_id, request.form.get("reason", ""), _version()
        )
        flash("已驳回，卖家可修改后重新提交", "success")
    except AppError as exc:
        flash(exc.message, "error")
    return redirect(url_for("admin.review"))


@admin_bp.route("/items")
@admin_required
def items():
    status = item_status_filter()
    keyword = (request.args.get("q") or "").strip()
    try:
        page = get_page()
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("admin.items"))
    rows = AuditService(get_db()).admin_list(status, keyword, page)
    return render_template(
        "admin/items.html", items=rows, page=page, status=status, keyword=keyword
    )


@admin_bp.route("/items/<int:item_id>/violation", methods=["POST"])
@admin_required
def violation(item_id: int):
    try:
        AuditService(get_db()).violation_delist(
            _admin_id(), item_id, request.form.get("reason", ""), _version()
        )
        flash("已违规下架，相关预约已联动取消", "success")
    except AppError as exc:
        flash(exc.message, "error")
    return redirect(url_for("admin.items"))


@admin_bp.route("/logs")
@admin_required
def logs():
    try:
        page = get_page()
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("admin.logs"))
    filters = log_filters_from_args()
    service = LogService(get_db())
    entries = service.query(filters, page)
    return render_template(
        "logs.html",
        logs=entries,
        page=page,
        actions=service.actions(),
        filters=request.args,
        scope="admin",
    )


@admin_bp.route("/stats")
@admin_required
def stats():
    overview = StatService(get_db()).admin_overview()
    return render_template("admin/stats.html", **overview)


@admin_bp.route("/dict")
@admin_required
def dicts():
    data = DictService(get_db()).list_all()
    return render_template("admin/dict.html", **data)


@admin_bp.route("/dict/category", methods=["POST"])
@admin_required
def category_action():
    service = DictService(get_db())
    try:
        if request.form.get("op") == "toggle":
            service.toggle_category(int(request.form.get("category_id", "0")))
            flash("分类状态已更新", "success")
        else:
            service.create_category(
                request.form.get("name", ""),
                int(request.form.get("sort_order", "0") or 0),
            )
            flash("分类已新增", "success")
    except (AppError, ValueError) as exc:
        flash(getattr(exc, "message", str(exc)), "error")
    return redirect(url_for("admin.dicts"))


@admin_bp.route("/dict/condition", methods=["POST"])
@admin_required
def condition_action():
    service = DictService(get_db())
    try:
        if request.form.get("op") == "toggle":
            service.toggle_condition(int(request.form.get("condition_id", "0")))
            flash("成色状态已更新", "success")
        else:
            service.create_condition(
                request.form.get("name", ""),
                int(request.form.get("sort_order", "0") or 0),
            )
            flash("成色已新增", "success")
    except (AppError, ValueError) as exc:
        flash(getattr(exc, "message", str(exc)), "error")
    return redirect(url_for("admin.dicts"))


def _admin_id() -> int:
    return current_user().user_id


def _version() -> int:
    try:
        return int(request.form.get("version", ""))
    except ValueError:
        return -1
