"""密码哈希与校验（bcrypt，cost=12）。"""

from __future__ import annotations

import os

import bcrypt

BCRYPT_ROUNDS = 12


def _rounds() -> int:
    """测试环境可通过环境变量降低 cost，生产默认 12。"""

    return int(os.environ.get("SECONDHAND_BCRYPT_ROUNDS", str(BCRYPT_ROUNDS)))


def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt(rounds=_rounds())
    ).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False
