"""
Classes Blueprint — /api/classes/*
"""
from __future__ import annotations

from flask import Blueprint, request, jsonify, g

from backend.database import get_conn
from backend.middleware.auth import require_auth
from backend.models.class_ import (
    list_classes_for_user, list_available_classes, create_class,
    update_class, delete_class, get_class_members,
    add_class_member, remove_class_member,
    request_join_class, review_join_request,
    get_pending_requests, get_available_students,
)
from backend.models.access import user_can_manage_class
from backend.services.sync_service import publish_user_updates
from backend.utils.file_utils import delete_courseware_assets
from backend.services.assignment_service import delete_assignment_assets

classes_bp = Blueprint("classes", __name__)


@classes_bp.route("/api/classes", methods=["GET"])
@require_auth
def get_classes():
    conn = get_conn()
    try:
        classes = list_classes_for_user(conn, g.current_user)
        return jsonify({"classes": classes}), 200
    finally:
        conn.close()


@classes_bp.route("/api/classes/available", methods=["GET"])
@require_auth
def available_classes():
    if g.current_user["role"] != "student":
        return jsonify({"error": "仅学生可查看可选班级。"}), 403
    conn = get_conn()
    try:
        classes = list_available_classes(conn, g.current_user["id"])
        return jsonify({"classes": classes}), 200
    finally:
        conn.close()


@classes_bp.route("/api/classes", methods=["POST"])
@require_auth
def create_class_route():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    description = (data.get("description") or "").strip()
    teacher_id = data.get("teacher_id")
    if not name:
        return jsonify({"error": "请输入班级名称。"}), 400

    conn = get_conn()
    try:
        if g.current_user["role"] == "admin":
            try:
                teacher_id = int(teacher_id)
            except (TypeError, ValueError):
                return jsonify({"error": "请选择授课教师。"}), 400
            teacher = conn.execute(
                "SELECT id FROM users WHERE id = ? AND role = 'teacher'", (teacher_id,)
            ).fetchone()
            if not teacher:
                return jsonify({"error": "授课教师不存在。"}), 400
        else:
            if g.current_user["role"] != "teacher":
                return jsonify({"error": "仅教师和管理员可创建班级。"}), 403
            teacher_id = g.current_user["id"]

        class_info = create_class(conn, name, description, teacher_id)
        conn.commit()
        publish_user_updates(g.current_user["id"], teacher_id)
        return jsonify({"classroom": class_info}), 201
    finally:
        conn.close()


@classes_bp.route("/api/classes/join", methods=["POST"])
@require_auth
def join_class():
    if g.current_user["role"] != "student":
        return jsonify({"error": "仅学生可申请加入班级。"}), 403
    data = request.get_json(silent=True) or {}
    try:
        class_id = int(data.get("class_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "请选择班级。"}), 400
    conn = get_conn()
    try:
        existing = request_join_class(conn, class_id, g.current_user["id"])
        if existing:
            if existing["status"] == "approved":
                return jsonify({"error": "你已经是该班级成员。"}), 400
            if existing["status"] == "pending":
                return jsonify({"error": "你已经提交过入班申请，请耐心等待教师审批。"}), 400
        conn.commit()
        teacher = conn.execute(
            "SELECT teacher_id FROM classes WHERE id = ?", (class_id,)
        ).fetchone()
        if teacher:
            publish_user_updates(teacher["teacher_id"])
        return jsonify({"message": "申请已提交，请等待教师审批。"}), 200
    finally:
        conn.close()


@classes_bp.route("/api/classes/<int:class_id>/members", methods=["GET"])
@require_auth
def get_class_members_route(class_id: int):
    conn = get_conn()
    try:
        members = get_class_members(conn, class_id)
        pending_requests = get_pending_requests(conn, class_id)
        available_students = get_available_students(conn, class_id)
        return jsonify({
            "members": members,
            "pending_requests": pending_requests,
            "available_students": available_students,
        }), 200
    finally:
        conn.close()


@classes_bp.route("/api/classes/<int:class_id>/members", methods=["POST"])
@require_auth
def add_class_member_route(class_id: int):
    conn = get_conn()
    try:
        if not user_can_manage_class(conn, g.current_user, class_id):
            return jsonify({"error": "当前账号无权管理该班级。"}), 403
        data = request.get_json(silent=True) or {}
        try:
            member_id = int(data.get("student_id") or data.get("user_id"))
        except (TypeError, ValueError):
            return jsonify({"error": "请选择要添加的成员。"}), 400
        member = conn.execute("SELECT id FROM users WHERE id = ?", (member_id,)).fetchone()
        if not member:
            return jsonify({"error": "用户不存在。"}), 404
        add_class_member(conn, class_id, member_id)
        conn.commit()
        publish_user_updates(member_id)
        return jsonify({"message": "成员已加入班级。"}), 200
    finally:
        conn.close()


@classes_bp.route("/api/classes/<int:class_id>", methods=["PUT"])
@require_auth
def update_class_route(class_id: int):
    conn = get_conn()
    try:
        if not user_can_manage_class(conn, g.current_user, class_id):
            return jsonify({"error": "当前账号无权管理该班级。"}), 403
        data = request.get_json(silent=True) or {}
        name = (data.get("name") or "").strip()
        description = (data.get("description") or "").strip()
        if not name:
            return jsonify({"error": "班级名称不能为空。"}), 400
        teacher_id = None
        if g.current_user["role"] == "admin" and data.get("teacher_id"):
            try:
                teacher_id = int(data["teacher_id"])
            except (TypeError, ValueError):
                return jsonify({"error": "教师编号不合法。"}), 400
        class_info = update_class(conn, class_id, name, description, teacher_id)
        publish_user_updates(*[m["id"] for m in get_class_members(conn, class_id)])
        return jsonify({"classroom": class_info}), 200
    finally:
        conn.close()


@classes_bp.route("/api/classes/<int:class_id>", methods=["DELETE"])
@require_auth
def delete_class_route(class_id: int):
    conn = get_conn()
    try:
        if not user_can_manage_class(conn, g.current_user, class_id):
            return jsonify({"error": "当前账号无权删除该班级。"}), 403
        result = delete_class(conn, class_id)
        conn.commit()
        for file_name in result["stored_file_names"]:
            delete_courseware_assets(file_name)
        for assignment_id in result.get("assignment_ids", []):
            delete_assignment_assets(assignment_id)
        publish_user_updates(*result["affected_user_ids"])
        return jsonify({"message": result["message"]}), 200
    finally:
        conn.close()


@classes_bp.route("/api/classes/<int:class_id>/members/<int:user_id>", methods=["DELETE"])
@require_auth
def remove_class_member_route(class_id: int, user_id: int):
    conn = get_conn()
    try:
        if not user_can_manage_class(conn, g.current_user, class_id):
            return jsonify({"error": "当前账号无权管理该班级。"}), 403
        remove_class_member(conn, class_id, user_id)
        conn.commit()
        publish_user_updates(user_id)
        return jsonify({"message": "成员已移除。"}), 200
    finally:
        conn.close()


@classes_bp.route("/api/classes/requests/<int:request_id>/approve", methods=["POST"])
@require_auth
def approve_join_request(request_id: int):
    conn = get_conn()
    try:
        result = review_join_request(conn, request_id, "approved", g.current_user["id"])
        if not result:
            return jsonify({"error": "申请不存在或已处理"}), 404
        conn.commit()
        publish_user_updates(result["student_id"])
        return jsonify({"message": "已通过入班申请。"}), 200
    finally:
        conn.close()


@classes_bp.route("/api/classes/requests/<int:request_id>/reject", methods=["POST"])
@require_auth
def reject_join_request(request_id: int):
    conn = get_conn()
    try:
        result = review_join_request(conn, request_id, "rejected", g.current_user["id"])
        if not result:
            return jsonify({"error": "申请不存在或已处理"}), 404
        conn.commit()
        return jsonify({"message": "已拒绝入班申请。"}), 200
    finally:
        conn.close()
