"""
Auth middleware — extracts current user from Authorization header.
"""
from __future__ import annotations

import sqlite3

from backend.database import get_conn
from backend.models.user import get_user_by_token


def get_current_user_from_token(token: str) -> dict | None:
    """Extract user from bearer token. Returns None if invalid."""
    if not token:
        return None
    conn = get_conn()
    try:
        return get_user_by_token(conn, token)
    finally:
        conn.close()


def require_user_from_header(auth_header: str | None) -> tuple[dict | None, str | None]:
    """
    Given an Authorization header value, return (user, error_message).
    If user is None, error_message contains the reason.
    """
    if not auth_header or not auth_header.startswith("Bearer "):
        return None, "未登录，请先登录。"
    token = auth_header.split(" ", 1)[1].strip()
    user = get_current_user_from_token(token)
    if not user:
        return None, "登录已过期，请重新登录。"
    return user, None
