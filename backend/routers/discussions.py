"""
Discussions router — /api/discussions/*
"""
from __future__ import annotations

import json
from http import HTTPStatus

from backend.database import get_conn
from backend.middleware.auth import require_user_from_header
from backend.models.discussion import (
    list_discussions, get_discussion_detail,
    create_discussion, create_reply,
)
from backend.models.access import build_class_scope_clause, user_can_access_class
from backend.services.sync_service import publish_user_updates


def handle_discussion_routes(path: str, method: str, headers: dict, body: bytes, query_params: dict) -> tuple[dict | list, int] | None:
    if not path.startswith("/api/discussions"):
        return None
    user, error = require_user_from_header(headers.get("Authorization"))
    if error:
        return {"error": error}, HTTPStatus.UNAUTHORIZED

    # GET /api/discussions
    if method == "GET" and path == "/api/discussions":
        conn = get_conn()
        try:
            class_id = query_params.get("class_id")
            if class_id:
                class_id = int(class_id[0])
                if not user_can_access_class(conn, user, class_id):
                    return {"error": "当前账号无权查看该班级讨论。"}, HTTPStatus.FORBIDDEN
            clause, params = build_class_scope_clause(user, class_id, "d.class_id")
            discussions = list_discussions(conn, clause, params, class_id)
            return {"discussions": discussions}, HTTPStatus.OK
        finally:
            conn.close()

    # POST /api/discussions
    if method == "POST" and path == "/api/discussions":
        data = json.loads(body) if body else {}
        title = (data.get("title") or "").strip()
        body_text = (data.get("body") or "").strip()
        try:
            class_id = int(data.get("class_id"))
        except (TypeError, ValueError):
            return {"error": "请选择班级。"}, HTTPStatus.BAD_REQUEST
        if not title or not body_text:
            return {"error": "标题和内容不能为空。"}, HTTPStatus.BAD_REQUEST

        conn = get_conn()
        try:
            if not user_can_access_class(conn, user, class_id):
                return {"error": "当前账号无权在该班级发起讨论。"}, HTTPStatus.FORBIDDEN
            discussion = create_discussion(conn, title, body_text, user["id"], class_id)
            conn.commit()
            return {"discussion": discussion}, HTTPStatus.CREATED
        finally:
            conn.close()

    # POST /api/discussions/{id}/replies
    if method == "POST" and "/replies" in path and path.startswith("/api/discussions/"):
        parts = path.split("/")
        try:
            discussion_id = int(parts[3])
        except (IndexError, ValueError):
            return {"error": "讨论编号不合法。"}, HTTPStatus.BAD_REQUEST
        data = json.loads(body) if body else {}
        body_text = (data.get("body") or "").strip()
        if not body_text:
            return {"error": "回复内容不能为空。"}, HTTPStatus.BAD_REQUEST

        conn = get_conn()
        try:
            discussion = get_discussion_detail(conn, discussion_id)
            if not discussion:
                return {"error": "讨论不存在。"}, HTTPStatus.NOT_FOUND
            if not user_can_access_class(conn, user, discussion["class_id"]):
                return {"error": "当前账号无权回复该讨论。"}, HTTPStatus.FORBIDDEN
            reply = create_reply(conn, discussion_id, body_text, user["id"])
            conn.commit()
            publish_user_updates(discussion["author_id"])
            return {"reply": reply}, HTTPStatus.CREATED
        finally:
            conn.close()

    return None
