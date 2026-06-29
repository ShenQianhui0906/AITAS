"""
Users Blueprint — /api/users/*
"""
from __future__ import annotations

from flask import Blueprint, request, jsonify, g

from backend.database import get_conn
from backend.middleware.auth import require_auth
from backend.models.user import (
    list_users, create_user, update_user, delete_user,
    check_username_exists, check_student_number_exists,
)
from backend.services.sync_service import publish_user_updates
from backend.utils.file_utils import delete_courseware_assets
from backend.services.assignment_service import delete_stored_assignment_file

users_bp = Blueprint("users", __name__)


@users_bp.route("/api/users", methods=["GET"])
@require_auth
def get_users():
    conn = get_conn()
    try:
        if g.current_user["role"] == "admin":
            users = list_users(conn)
            return jsonify({"users": users}), 200
        else:
            rows = conn.execute(
                "SELECT id, username, display_name, role, student_number, created_at "
                "FROM users WHERE id != ? ORDER BY CASE role WHEN 'teacher' THEN 0 ELSE 1 END, display_name ASC",
                (g.current_user["id"],),
            ).fetchall()
            return jsonify({"users": [dict(r) for r in rows]}), 200
    finally:
        conn.close()


@users_bp.route("/api/users", methods=["POST"])
@require_auth
def create_user_route():
    if g.current_user["role"] != "admin":
        return jsonify({"error": "仅管理员可创建用户。"}), 403
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    display_name = (data.get("display_name") or "").strip()
    password = data.get("password") or ""
    role = (data.get("role") or "").strip()
    student_number = (data.get("student_number") or "").strip()

    if not username or not display_name or not password or role not in {"teacher", "student"}:
        return jsonify({"error": "请完整填写用户信息。"}), 400
    if role == "student" and not student_number:
        return jsonify({"error": "创建学生时请填写学号。"}), 400

    conn = get_conn()
    try:
        if check_username_exists(conn, username):
            return jsonify({"error": "用户名已存在。"}), 400
        if role == "student" and check_student_number_exists(conn, student_number):
            return jsonify({"error": "学号已存在。"}), 400
        new_user, _token = create_user(conn, username, display_name, role, password, student_number)
        conn.commit()
        return jsonify({"user": new_user}), 201
    finally:
        conn.close()


@users_bp.route("/api/users/<int:user_id>", methods=["PUT"])
@require_auth
def update_user_route(user_id: int):
    if g.current_user["role"] != "admin":
        return jsonify({"error": "仅管理员可修改用户。"}), 403

    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    display_name = (data.get("display_name") or "").strip()
    role = (data.get("role") or "").strip()
    student_number = (data.get("student_number") or "").strip()
    password = data.get("password") or ""

    if not username or not display_name:
        return jsonify({"error": "用户名和姓名不能为空。"}), 400

    conn = get_conn()
    try:
        target = conn.execute("SELECT id, role FROM users WHERE id = ?", (user_id,)).fetchone()
        if not target:
            return jsonify({"error": "用户不存在。"}), 404
        if target["role"] == "admin":
            return jsonify({"error": "管理员账号不支持在此页面修改。"}), 400
        if role not in {"teacher", "student"}:
            return jsonify({"error": "仅支持维护教师和学生账号。"}), 400
        if role == "student" and not student_number:
            return jsonify({"error": "学生账号必须填写学号。"}), 400

        if check_username_exists(conn, username, user_id):
            return jsonify({"error": "用户名已存在。"}), 400
        if role == "student" and check_student_number_exists(conn, student_number, user_id):
            return jsonify({"error": "学号已存在。"}), 400

        updated = update_user(conn, user_id, username, display_name, role, student_number, password or None)
        conn.commit()
        publish_user_updates(user_id)
        return jsonify({"user": updated, "message": "用户信息已更新。"}), 200
    finally:
        conn.close()


@users_bp.route("/api/users/<int:user_id>", methods=["DELETE"])
@require_auth
def delete_user_route(user_id: int):
    if g.current_user["role"] != "admin":
        return jsonify({"error": "仅管理员可删除用户。"}), 403

    conn = get_conn()
    try:
        target = conn.execute("SELECT id, role FROM users WHERE id = ?", (user_id,)).fetchone()
        if not target:
            return jsonify({"error": "用户不存在。"}), 404
        if target["role"] == "admin":
            return jsonify({"error": "管理员账号不支持删除。"}), 400

        result = delete_user(conn, user_id)
        conn.commit()
        for file_name in result["stored_file_names"]:
            delete_courseware_assets(file_name)
        for file_name in result.get("assignment_file_names", []):
            delete_stored_assignment_file(file_name)
        publish_user_updates(*result["affected_user_ids"])
        return jsonify({"message": "用户已删除。"}), 200
    finally:
        conn.close()
