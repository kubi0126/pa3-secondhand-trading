"""轻量 CSRF 防护：会话 token + 表单隐藏字段。"""

from __future__ import annotations

import hmac
import secrets

from flask import abort, current_app, request, session

FORM_FIELD = "_csrf"


def csrf_token() -> str:
    token = session.get(FORM_FIELD)
    if not token:
        token = secrets.token_urlsafe(32)
        session[FORM_FIELD] = token
    return token


def validate_csrf() -> None:
    if not current_app.config.get("CSRF_ENABLED", True):
        return
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return
    submitted = request.form.get(FORM_FIELD) or request.headers.get("X-CSRF-Token", "")
    expected = session.get(FORM_FIELD, "")
    if not submitted or not expected or not hmac.compare_digest(submitted, expected):
        abort(400, description="CSRF 校验失败，请刷新页面后重试")
