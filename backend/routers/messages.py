"""
Messages router — /api/messages/*
"""
from __future__ import annotations

import json
from http import HTTPStatus

from backend.database import get_conn
from backend.middleware.auth import require_user_from_header
from backend.models.message import (
    list_contacts, list_conversations, list_thread_messages,
    send_message, create_conversation, delete_conversation,
)
from backend.models.access import users_share_class
from backend.services.sync_service import publish_user_updates, get_user_sync_cursor, wait_for_user_update


def handle_message_routes(path: str, method: str, headers: dict, body: bytes, query_params: dict) -> tuple[dict | list, int] | None:
    if not path.startswith("/api/messages"):
        return None
    user, error = require_user_from_header(headers.get("Authorization"))
    if error:
        return {"error": error}, HTTPStatus.UNAUTHORIZED

    # GET /api/messages/contacts
    if method == "GET" and path == "/api/messages/contacts":
        conn = get_conn()
        try:
            contacts = list_contacts(conn, user["id"])
            return {"contacts": contacts}, HTTPStatus.OK
        finally:
            conn.close()

    # GET /api/messages/conversations
    if method == "GET" and path == "/api/messages/conversations":
        conn = get_conn()
        try:
            conversations = list_conversations(conn, user["id"])
            return {"conversations": conversations}, HTTPStatus.OK
        finally:
            conn.close()

    # GET /api/messages/events (SSE)
    if method == "GET" and path == "/api/messages/events":
        cursor = get_user_sync_cursor(user["id"])
        new_cursor = wait_for_user_update(user["id"], cursor, timeout=25.0)
        if new_cursor is not None:
            return {"cursor": new_cursor, "updates": True}, HTTPStatus.OK
        return {"cursor": cursor, "updates": False}, HTTPStatus.OK

    # GET /api/messages/thread/{id}
    if method == "GET" and path.startswith("/api/messages/thread/"):
        parts = path.split("/")
        try:
            thread_id = int(parts[-1])
        except (IndexError, ValueError):
            return {"error": "会话编号不合法。"}, HTTPStatus.BAD_REQUEST
        conn = get_conn()
        try:
            # Verify access
            member = conn.execute(
                "SELECT 1 FROM conversation_members WHERE thread_id = ? AND user_id = ? AND visible = 1",
                (thread_id, user["id"]),
            ).fetchone()
            if not member:
                return {"error": "会话不存在。"}, HTTPStatus.NOT_FOUND

            messages = list_thread_messages(conn, thread_id, user["id"])
            # Get other user
            other_row = conn.execute(
                "SELECT u.id, u.username, u.display_name, u.role, u.student_number "
                "FROM conversation_members cm JOIN users u ON u.id = cm.user_id "
                "WHERE cm.thread_id = ? AND cm.user_id != ?",
                (thread_id, user["id"]),
            ).fetchone()
            return {
                "thread_id": thread_id,
                "other_user": dict(other_row) if other_row else None,
                "messages": messages,
            }, HTTPStatus.OK
        finally:
            conn.close()

    # POST /api/messages/conversations
    if method == "POST" and path == "/api/messages/conversations":
        data = json.loads(body) if body else {}
        try:
            other_id = int(data.get("user_id"))
        except (TypeError, ValueError):
            return {"error": "联系人参数不合法。"}, HTTPStatus.BAD_REQUEST
        conn = get_conn()
        try:
            other = conn.execute("SELECT * FROM users WHERE id = ?", (other_id,)).fetchone()
            if not other:
                return {"error": "用户不存在。"}, HTTPStatus.NOT_FOUND
            if not users_share_class(conn, user["id"], other_id):
                return {"error": "仅可查看同班联系人会话。"}, HTTPStatus.FORBIDDEN

            thread_id = create_conversation(conn, user["id"], other_id)
            conn.commit()
            return {
                "thread_id": thread_id,
                "other_user": {
                    "id": other["id"], "username": other["username"],
                    "display_name": other["display_name"], "role": other["role"],
                    "student_number": other["student_number"],
                },
                "messages": [],
            }, HTTPStatus.OK
        finally:
            conn.close()

    # POST /api/messages
    if method == "POST" and path == "/api/messages":
        data = json.loads(body) if body else {}
        try:
            receiver_id = int(data.get("receiver_id"))
        except (TypeError, ValueError):
            return {"error": "接收人参数不合法。"}, HTTPStatus.BAD_REQUEST
        body_text = (data.get("body") or "").strip()
        if not body_text:
            return {"error": "消息内容不能为空。"}, HTTPStatus.BAD_REQUEST

        conn = get_conn()
        try:
            receiver = conn.execute("SELECT id FROM users WHERE id = ?", (receiver_id,)).fetchone()
            if not receiver:
                return {"error": "接收人不存在。"}, HTTPStatus.NOT_FOUND
            if not users_share_class(conn, user["id"], receiver_id):
                return {"error": "仅可向同班联系人发送私信。"}, HTTPStatus.FORBIDDEN

            send_message(conn, user["id"], receiver_id, body_text)
            conn.commit()
            publish_user_updates(user["id"], receiver_id)
            return {"message": "消息发送成功。"}, HTTPStatus.CREATED
        finally:
            conn.close()

    # DELETE /api/messages/conversations/{id}
    if method == "DELETE" and path.startswith("/api/messages/conversations/"):
        parts = path.split("/")
        try:
            thread_id = int(parts[-1])
        except (IndexError, ValueError):
            return {"error": "会话编号不合法。"}, HTTPStatus.BAD_REQUEST
        conn = get_conn()
        try:
            delete_conversation(conn, thread_id, user["id"])
            conn.commit()
            return {"message": "会话已删除。"}, HTTPStatus.OK
        finally:
            conn.close()

    return None
