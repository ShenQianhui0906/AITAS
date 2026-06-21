"""
Classes router — /api/classes/*
"""
from __future__ import annotations

import json
from http import HTTPStatus

from backend.database import get_conn
from backend.middleware.auth import require_user_from_header
from backend.models.class_ import (
    list_classes_for_user, list_available_classes, create_class,
    update_class, delete_class, get_class_members,
    add_class_member, remove_class_member,
    request_join_class, review_join_request,
)
from backend.models.access import user_can_manage_class
from backend.services.sync_service import publish_user_updates
from backend.utils.file_utils import delete_courseware_assets


def handle_class_routes(path: str, method: str, headers: dict, body: bytes, query_params: dict) -> tuple[dict | list, int] | None:
    if not path.startswith("/api/classes"):
        return None
    user, error = require_user_from_header(headers.get("Authorization"))
    if error:
        return {"error": error}, HTTPStatus.UNAUTHORIZED

    # GET /api/classes
    if method == "GET" and path == "/api/classes":
        conn = get_conn()
        try:
            classes = list_classes_for_user(conn, user)
            return {"classes": classes}, HTTPStatus.OK
        finally:
            conn.close()

    # GET /api/classes/available
    if method == "GET" and path == "/api/classes/available":
        if user["role"] != "student":
            return {"error": "仅学生可查看可选班级。"}, HTTPStatus.FORBIDDEN
        conn = get_conn()
        try:
            classes = list_available_classes(conn, user["id"])
            return {"classes": classes}, HTTPStatus.OK
        finally:
            conn.close()

    # POST /api/classes
    if method == "POST" and path == "/api/classes":
        data = json.loads(body) if body else {}
        name = (data.get("name") or "").strip()
        description = (data.get("description") or "").strip()
        teacher_id = data.get("teacher_id")
        if not name:
            return {"error": "请输入班级名称。"}, HTTPStatus.BAD_REQUEST

        conn = get_conn()
        try:
            if user["role"] == "admin":
                try:
                    teacher_id = int(teacher_id)
                except (TypeError, ValueError):
                    return {"error": "请选择授课教师。"}, HTTPStatus.BAD_REQUEST
                teacher = conn.execute(
                    "SELECT id FROM users WHERE id = ? AND role = 'teacher'", (teacher_id,)
                ).fetchone()
                if not teacher:
                    return {"error": "授课教师不存在。"}, HTTPStatus.BAD_REQUEST
            else:
                if user["role"] != "teacher":
                    return {"error": "仅教师和管理员可创建班级。"}, HTTPStatus.FORBIDDEN
                teacher_id = user["id"]

            class_info = create_class(conn, name, description, teacher_id)
            conn.commit()
            publish_user_updates(user["id"], teacher_id)
            return {"classroom": class_info}, HTTPStatus.CREATED
        finally:
            conn.close()

    # POST /api/classes/join
    if method == "POST" and path == "/api/classes/join":
        if user["role"] != "student":
            return {"error": "仅学生可申请加入班级。"}, HTTPStatus.FORBIDDEN
        data = json.loads(body) if body else {}
        try:
            class_id = int(data.get("class_id"))
        except (TypeError, ValueError):
            return {"error": "请选择班级。"}, HTTPStatus.BAD_REQUEST
        conn = get_conn()
        try:
            existing = request_join_class(conn, class_id, user["id"])
            if existing:
                if existing["status"] == "approved":
                    return {"error": "你已经是该班级成员。"}, HTTPStatus.BAD_REQUEST
                if existing["status"] == "pending":
                    return {"error": "你已经提交过入班申请，请耐心等待教师审批。"}, HTTPStatus.BAD_REQUEST
            conn.commit()
            teacher = conn.execute(
                "SELECT teacher_id FROM classes WHERE id = ?", (class_id,)
            ).fetchone()
            if teacher:
                publish_user_updates(teacher["teacher_id"])
            return {"message": "申请已提交，请等待教师审批。"}, HTTPStatus.OK
        finally:
            conn.close()

    # GET /api/classes/{id}/members
    if method == "GET" and "/members" in path and path.startswith("/api/classes/"):
        parts = path.split("/")
        try:
            class_id = int(parts[3])
        except (IndexError, ValueError):
            return {"error": "班级编号不合法。"}, HTTPStatus.BAD_REQUEST
        conn = get_conn()
        try:
            members = get_class_members(conn, class_id)
            return {"members": members}, HTTPStatus.OK
        finally:
            conn.close()

    # POST /api/classes/{id}/members
    if method == "POST" and "/members" in path and path.startswith("/api/classes/"):
        parts = path.split("/")
        try:
            class_id = int(parts[3])
        except (IndexError, ValueError):
            return {"error": "班级编号不合法。"}, HTTPStatus.BAD_REQUEST
        conn = get_conn()
        try:
            if not user_can_manage_class(conn, user, class_id):
                return {"error": "当前账号无权管理该班级。"}, HTTPStatus.FORBIDDEN
            data = json.loads(body) if body else {}
            try:
                member_id = int(data.get("user_id"))
            except (TypeError, ValueError):
                return {"error": "请选择要添加的成员。"}, HTTPStatus.BAD_REQUEST
            member = conn.execute("SELECT id FROM users WHERE id = ?", (member_id,)).fetchone()
            if not member:
                return {"error": "用户不存在。"}, HTTPStatus.NOT_FOUND
            add_class_member(conn, class_id, member_id)
            conn.commit()
            publish_user_updates(member_id)
            return {"message": "成员已加入班级。"}, HTTPStatus.OK
        finally:
            conn.close()

    # PUT /api/classes/{id}
    if method == "PUT" and path.startswith("/api/classes/") and "/members/" not in path and "/requests/" not in path:
        parts = path.split("/")
        try:
            class_id = int(parts[3])
        except (IndexError, ValueError):
            return {"error": "班级编号不合法。"}, HTTPStatus.BAD_REQUEST
        conn = get_conn()
        try:
            if not user_can_manage_class(conn, user, class_id):
                return {"error": "当前账号无权管理该班级。"}, HTTPStatus.FORBIDDEN
            data = json.loads(body) if body else {}
            name = (data.get("name") or "").strip()
            description = (data.get("description") or "").strip()
            if not name:
                return {"error": "班级名称不能为空。"}, HTTPStatus.BAD_REQUEST
            teacher_id = None
            if user["role"] == "admin" and data.get("teacher_id"):
                try:
                    teacher_id = int(data["teacher_id"])
                except (TypeError, ValueError):
                    return {"error": "教师编号不合法。"}, HTTPStatus.BAD_REQUEST
            class_info = update_class(conn, class_id, name, description, teacher_id)
            publish_user_updates(*[m["id"] for m in get_class_members(conn, class_id)])
            return {"classroom": class_info}, HTTPStatus.OK
        finally:
            conn.close()

    # DELETE /api/classes/{id}/members/{user_id}
    if method == "DELETE" and "/members/" in path and path.startswith("/api/classes/"):
        parts = path.split("/")
        try:
            class_id = int(parts[3])
            member_id = int(parts[-1])
        except (IndexError, ValueError):
            return {"error": "参数不合法。"}, HTTPStatus.BAD_REQUEST
        conn = get_conn()
        try:
            if not user_can_manage_class(conn, user, class_id):
                return {"error": "当前账号无权管理该班级。"}, HTTPStatus.FORBIDDEN
            remove_class_member(conn, class_id, member_id)
            conn.commit()
            publish_user_updates(member_id)
            return {"message": "成员已移除。"}, HTTPStatus.OK
        finally:
            conn.close()

    # DELETE /api/classes/{id}
    if method == "DELETE" and path.startswith("/api/classes/"):
        parts = path.split("/")
        try:
            class_id = int(parts[3])
        except (IndexError, ValueError):
            return {"error": "班级编号不合法。"}, HTTPStatus.BAD_REQUEST
        conn = get_conn()
        try:
            if not user_can_manage_class(conn, user, class_id):
                return {"error": "当前账号无权管理该班级。"}, HTTPStatus.FORBIDDEN
            result = delete_class(conn, class_id)
            conn.commit()
            for file_name in result["stored_file_names"]:
                delete_courseware_assets(file_name)
            publish_user_updates(*result["affected_user_ids"])
            return {"message": "班级已删除。"}, HTTPStatus.OK
        finally:
            conn.close()

    # POST /api/classes/requests/{id}/approve or /reject
    if method == "POST" and "/requests/" in path:
        parts = path.split("/")
        decision = parts[-1] if parts[-1] in ("approve", "reject") else None
        try:
            request_id = int(parts[4])
        except (IndexError, ValueError):
            return {"error": "请求编号不合法。"}, HTTPStatus.BAD_REQUEST
        if decision not in ("approve", "reject"):
            return {"error": "审批操作不合法。"}, HTTPStatus.BAD_REQUEST

        conn = get_conn()
        try:
            decision_mapped = "approved" if decision == "approve" else "rejected"
            result = review_join_request(conn, request_id, decision_mapped, user["id"])
            if not result:
                return {"error": "该申请不存在或已处理。"}, HTTPStatus.NOT_FOUND
            if not user_can_manage_class(conn, user, result["class_id"]):
                return {"error": "当前账号无权审批该申请。"}, HTTPStatus.FORBIDDEN
            conn.commit()
            publish_user_updates(result["student_id"])
            return {"message": "申请已处理。"}, HTTPStatus.OK
        finally:
            conn.close()

    return None
