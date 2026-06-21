"""
Users router — /api/users/*
"""
from __future__ import annotations

import json
from http import HTTPStatus

from backend.database import get_conn
from backend.middleware.auth import require_user_from_header
from backend.models.user import (
    list_users, create_user, update_user, delete_user,
    check_username_exists, check_student_number_exists,
)
from backend.services.sync_service import publish_user_updates
from backend.utils.file_utils import delete_courseware_assets


def handle_user_routes(path: str, method: str, headers: dict, body: bytes) -> tuple[dict | list, int] | None:
    if not path.startswith("/api/users"):
        return None
    user, error = require_user_from_header(headers.get("Authorization"))
    if error:
        return {"error": error}, HTTPStatus.UNAUTHORIZED

    # GET /api/users
    if method == "GET" and path == "/api/users":
        conn = get_conn()
        try:
            if user["role"] == "admin":
                users = list_users(conn)
                return {"users": users}, HTTPStatus.OK
            else:
                # Non-admin users see other users
                rows = conn.execute(
                    "SELECT id, username, display_name, role, student_number, created_at "
                    "FROM users WHERE id != ? ORDER BY CASE role WHEN 'teacher' THEN 0 ELSE 1 END, display_name ASC",
                    (user["id"],),
                ).fetchall()
                return {"users": [dict(r) for r in rows]}, HTTPStatus.OK
        finally:
            conn.close()

    # POST /api/users (admin only)
    if method == "POST" and path == "/api/users":
        if user["role"] != "admin":
            return {"error": "仅管理员可创建用户。"}, HTTPStatus.FORBIDDEN
        data = json.loads(body) if body else {}
        username = (data.get("username") or "").strip()
        display_name = (data.get("display_name") or "").strip()
        password = data.get("password") or ""
        role = (data.get("role") or "").strip()
        student_number = (data.get("student_number") or "").strip()

        if not username or not display_name or not password or role not in {"teacher", "student"}:
            return {"error": "请完整填写用户信息。"}, HTTPStatus.BAD_REQUEST
        if role == "student" and not student_number:
            return {"error": "创建学生时请填写学号。"}, HTTPStatus.BAD_REQUEST

        conn = get_conn()
        try:
            if check_username_exists(conn, username):
                return {"error": "用户名已存在。"}, HTTPStatus.BAD_REQUEST
            if role == "student" and check_student_number_exists(conn, student_number):
                return {"error": "学号已存在。"}, HTTPStatus.BAD_REQUEST

            new_user, _token = create_user(conn, username, display_name, role, password, student_number)
            conn.commit()
            return {"user": new_user}, HTTPStatus.CREATED
        finally:
            conn.close()

    # PUT /api/users/{id}
    if method == "PUT" and path.startswith("/api/users/"):
        parts = path.split("/")
        try:
            target_id = int(parts[3])
        except (IndexError, ValueError):
            return {"error": "用户编号不合法。"}, HTTPStatus.BAD_REQUEST

        if user["role"] != "admin":
            return {"error": "仅管理员可修改用户。"}, HTTPStatus.FORBIDDEN

        data = json.loads(body) if body else {}
        username = (data.get("username") or "").strip()
        display_name = (data.get("display_name") or "").strip()
        role = (data.get("role") or "").strip()
        student_number = (data.get("student_number") or "").strip()
        password = data.get("password") or ""

        if not username or not display_name:
            return {"error": "用户名和姓名不能为空。"}, HTTPStatus.BAD_REQUEST

        conn = get_conn()
        try:
            target = conn.execute("SELECT id, role FROM users WHERE id = ?", (target_id,)).fetchone()
            if not target:
                return {"error": "用户不存在。"}, HTTPStatus.NOT_FOUND
            if target["role"] == "admin":
                return {"error": "管理员账号不支持在此页面修改。"}, HTTPStatus.BAD_REQUEST
            if role not in {"teacher", "student"}:
                return {"error": "仅支持维护教师和学生账号。"}, HTTPStatus.BAD_REQUEST
            if role == "student" and not student_number:
                return {"error": "学生账号必须填写学号。"}, HTTPStatus.BAD_REQUEST

            if check_username_exists(conn, username, target_id):
                return {"error": "用户名已存在。"}, HTTPStatus.BAD_REQUEST
            if role == "student" and check_student_number_exists(conn, student_number, target_id):
                return {"error": "学号已存在。"}, HTTPStatus.BAD_REQUEST

            updated = update_user(conn, target_id, username, display_name, role, student_number, password or None)
            conn.commit()
            publish_user_updates(target_id)
            return {"user": updated, "message": "用户信息已更新。"}, HTTPStatus.OK
        finally:
            conn.close()

    # DELETE /api/users/{id}
    if method == "DELETE" and path.startswith("/api/users/"):
        parts = path.split("/")
        try:
            target_id = int(parts[3])
        except (IndexError, ValueError):
            return {"error": "用户编号不合法。"}, HTTPStatus.BAD_REQUEST

        if user["role"] != "admin":
            return {"error": "仅管理员可删除用户。"}, HTTPStatus.FORBIDDEN

        conn = get_conn()
        try:
            target = conn.execute("SELECT id, role FROM users WHERE id = ?", (target_id,)).fetchone()
            if not target:
                return {"error": "用户不存在。"}, HTTPStatus.NOT_FOUND
            if target["role"] == "admin":
                return {"error": "管理员账号不支持删除。"}, HTTPStatus.BAD_REQUEST

            result = delete_user(conn, target_id)
            conn.commit()
            for file_name in result["stored_file_names"]:
                delete_courseware_assets(file_name)
            publish_user_updates(*result["affected_user_ids"])
            return {"message": "用户已删除。"}, HTTPStatus.OK
        finally:
            conn.close()

    return None
