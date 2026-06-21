"""
Auth router — /api/auth/login, /api/auth/register, /api/auth/logout, /api/me
"""
from __future__ import annotations

import json
from http import HTTPStatus

from backend.database import get_conn
from backend.middleware.auth import require_user_from_header
from backend.models.user import authenticate_user, create_user, logout_user, get_user_by_id
from backend.services.sync_service import publish_user_updates


def handle_auth_routes(path: str, method: str, headers: dict, body: bytes) -> tuple[dict | list, int] | None:
    """Route auth-related API requests. Returns (response_data, status_code) or None."""
    if not (path == "/api/me" or path.startswith("/api/auth/")):
        return None

    # GET /api/me
    if method == "GET" and path == "/api/me":
        user, error = require_user_from_header(headers.get("Authorization"))
        if error:
            return {"error": error}, HTTPStatus.UNAUTHORIZED
        return {"user": user}, HTTPStatus.OK

    # POST /api/auth/login
    if method == "POST" and path == "/api/auth/login":
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            return {"error": "请求格式错误。"}, HTTPStatus.BAD_REQUEST
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        if not username or not password:
            return {"error": "请输入用户名和密码。"}, HTTPStatus.BAD_REQUEST
        conn = get_conn()
        try:
            user, token = authenticate_user(conn, username, password)
            if not user:
                return {"error": "用户名或密码错误。"}, HTTPStatus.UNAUTHORIZED
            conn.commit()
            return {"token": token, "user": user}, HTTPStatus.OK
        finally:
            conn.close()

    # POST /api/auth/register
    if method == "POST" and path == "/api/auth/register":
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            return {"error": "请求格式错误。"}, HTTPStatus.BAD_REQUEST
        username = (data.get("username") or "").strip()
        display_name = (data.get("display_name") or "").strip()
        password = data.get("password") or ""
        role = (data.get("role") or "").strip()
        student_number = (data.get("student_number") or "").strip()
        if not username or not display_name or not password or role not in {"teacher", "student"}:
            return {"error": "请完整填写注册信息。"}, HTTPStatus.BAD_REQUEST
        if role == "student" and not student_number:
            return {"error": "学生注册时请填写学号。"}, HTTPStatus.BAD_REQUEST
        conn = get_conn()
        try:
            if conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone():
                return {"error": "用户名已存在。"}, HTTPStatus.BAD_REQUEST
            if role == "student" and conn.execute(
                "SELECT id FROM users WHERE student_number = ?", (student_number,)
            ).fetchone():
                return {"error": "学号已存在。"}, HTTPStatus.BAD_REQUEST
            user, token = create_user(conn, username, display_name, role, password, student_number)
            conn.commit()
            return {"token": token, "user": user}, HTTPStatus.CREATED
        finally:
            conn.close()

    # POST /api/auth/logout
    if method == "POST" and path == "/api/auth/logout":
        user, error = require_user_from_header(headers.get("Authorization"))
        if error:
            return {"error": error}, HTTPStatus.UNAUTHORIZED
        token = headers["Authorization"].split(" ", 1)[1].strip()
        conn = get_conn()
        try:
            logout_user(conn, token)
            conn.commit()
            return {"message": "已退出登录。"}, HTTPStatus.OK
        finally:
            conn.close()

    return None  # not handled by this router
