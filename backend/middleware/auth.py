"""
Auth middleware — extracts current user from Authorization header.
Provides both the original function interface and a Flask decorator.
"""
from __future__ import annotations

import sqlite3
from functools import wraps
from flask import request, g, jsonify

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


# ── Flask decorator ──

def require_auth(f):
    """Flask decorator: injects current user into g.current_user, or returns 401."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        user, error = require_user_from_header(auth_header)
        if error:
            return jsonify({"error": error}), 401
        g.current_user = user
        return f(*args, **kwargs)
    return decorated

