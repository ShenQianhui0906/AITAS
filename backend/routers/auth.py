"""
Auth Blueprint — /api/auth/login, /api/auth/register, /api/auth/logout, /api/me
"""
from __future__ import annotations

from flask import Blueprint, request, jsonify

from backend.database import get_conn
from backend.middleware.auth import require_auth
from backend.models.user import authenticate_user, create_user, logout_user, get_user_by_id
from backend.services.sync_service import publish_user_updates

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/api/me", methods=["GET"])
@require_auth
def me():
    from flask import g
    return jsonify({"user": g.current_user}), 200


@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return jsonify({"error": "请输入用户名和密码。"}), 400
    conn = get_conn()
    try:
        user, token = authenticate_user(conn, username, password)
        if not user:
            return jsonify({"error": "用户名或密码错误。"}), 401
        conn.commit()
        return jsonify({"token": token, "user": user}), 200
    finally:
        conn.close()


@auth_bp.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    display_name = (data.get("display_name") or "").strip()
    password = data.get("password") or ""
    role = (data.get("role") or "").strip()
    student_number = (data.get("student_number") or "").strip()
    if not username or not display_name or not password or role not in {"teacher", "student"}:
        return jsonify({"error": "请完整填写注册信息。"}), 400
    if role == "student" and not student_number:
        return jsonify({"error": "学生注册时请填写学号。"}), 400
    conn = get_conn()
    try:
        if conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone():
            return jsonify({"error": "用户名已存在。"}), 400
        if role == "student" and conn.execute(
            "SELECT id FROM users WHERE student_number = ?", (student_number,)
        ).fetchone():
            return jsonify({"error": "学号已存在。"}), 400
        user, token = create_user(conn, username, display_name, role, password, student_number)
        conn.commit()
        return jsonify({"token": token, "user": user}), 201
    finally:
        conn.close()


@auth_bp.route("/api/auth/logout", methods=["POST"])
@require_auth
def logout():
    from flask import g
    token = request.headers.get("Authorization", "").split(" ", 1)[-1].strip()
    conn = get_conn()
    try:
        logout_user(conn, token)
        conn.commit()
        return jsonify({"message": "已退出登录。"}), 200
    finally:
        conn.close()

