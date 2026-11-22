"""业务异常。"""

from __future__ import annotations


class AppError(Exception):
    """所有业务异常的基类，带 HTTP 状态码与稳定错误码。"""

    status_code = 400
    code = "BAD_REQUEST"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code


class ValidationError(AppError):
    status_code = 422
    code = "VALIDATION_ERROR"


class AuthError(AppError):
    status_code = 401
    code = "UNAUTHORIZED"


class AccountLocked(AuthError):
    status_code = 423
    code = "ACCOUNT_LOCKED"


class PermissionDenied(AppError):
    status_code = 403
    code = "FORBIDDEN"


class NotFound(AppError):
    status_code = 404
    code = "NOT_FOUND"


class StateConflict(AppError):
    """状态不允许、版本号不一致或唯一约束冲突。"""

    status_code = 409
    code = "STATE_CONFLICT"


class DuplicateRequest(AppError):
    """幂等键正在处理中或已处理。"""

    status_code = 409
    code = "DUPLICATE_REQUEST"
