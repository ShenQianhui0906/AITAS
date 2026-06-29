"""
Messages Blueprint — /api/messages/*
"""
from __future__ import annotations

from flask import Blueprint, request, jsonify, g, current_app

from backend.database import get_conn
from backend.middleware.auth import require_auth
from backend.models.message import (
    list_contacts, list_conversations, list_thread_messages,
    send_message, create_conversation, delete_conversation,
)
from backend.models.access import users_share_class
from backend.services.sync_service import publish_user_updates, get_user_sync_cursor, wait_for_user_update
from backend.services.notification_service import notify_new_message

messages_bp = Blueprint("messages", __name__)


@messages_bp.route("/api/messages/contacts", methods=["GET"])
@require_auth
def get_contacts():
    class_id = request.args.get("class_id", type=int)
    conn = get_conn()
    try:
        contacts = list_contacts(conn, g.current_user["id"], class_id)
        return jsonify({"contacts": contacts}), 200
    finally:
        conn.close()


@messages_bp.route("/api/messages/conversations", methods=["GET"])
@require_auth
def get_conversations():
    conn = get_conn()
    try:
        conversations = list_conversations(conn, g.current_user["id"])
        return jsonify({"conversations": conversations}), 200
    finally:
        conn.close()


@messages_bp.route("/api/messages/events", methods=["GET"])
@require_auth
def events():
    cursor = request.args.get("cursor", default=0, type=int)
    if cursor < 0:
        cursor = 0
    current_cursor = get_user_sync_cursor(g.current_user["id"])
    if cursor > current_cursor:
        cursor = current_cursor
    new_cursor = wait_for_user_update(g.current_user["id"], cursor, timeout=25.0)
    if new_cursor is not None:
        return jsonify({"cursor": new_cursor, "changed": True, "updates": True}), 200
    current_cursor = get_user_sync_cursor(g.current_user["id"])
    return jsonify({"cursor": current_cursor, "changed": False, "updates": False}), 200


@messages_bp.route("/api/messages/thread/<int:thread_id>", methods=["GET"])
@require_auth
def get_thread(thread_id: int):
    conn = get_conn()
    try:
        member = conn.execute(
            "SELECT 1 FROM conversation_members WHERE thread_id = ? AND user_id = ? AND visible = 1",
            (thread_id, g.current_user["id"]),
        ).fetchone()
        if not member:
            return jsonify({"error": "会话不存在。"}), 404

        messages = list_thread_messages(conn, thread_id, g.current_user["id"])
        other_row = conn.execute(
            "SELECT u.id, u.username, u.display_name, u.role, u.student_number "
            "FROM conversation_members cm JOIN users u ON u.id = cm.user_id "
            "WHERE cm.thread_id = ? AND cm.user_id != ?",
            (thread_id, g.current_user["id"]),
        ).fetchone()
        return jsonify({
            "thread_id": thread_id,
            "other_user": dict(other_row) if other_row else None,
            "messages": messages,
        }), 200
    finally:
        conn.close()


@messages_bp.route("/api/messages/conversations", methods=["POST"])
@require_auth
def create_conversation_route():
    data = request.get_json(silent=True) or {}
    try:
        other_id = int(data.get("user_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "联系人参数不合法。"}), 400
    if other_id == g.current_user["id"]:
        return jsonify({"error": "不能与自己建立私信会话。"}), 400
    conn = get_conn()
    try:
        other = conn.execute("SELECT * FROM users WHERE id = ?", (other_id,)).fetchone()
        if not other:
            return jsonify({"error": "用户不存在。"}), 404
        if not users_share_class(conn, g.current_user["id"], other_id):
            return jsonify({"error": "仅可查看同班联系人会话。"}), 403

        thread_id = create_conversation(conn, g.current_user["id"], other_id)
        conn.commit()
        return jsonify({
            "thread_id": thread_id,
            "other_user": {
                "id": other["id"], "username": other["username"],
                "display_name": other["display_name"], "role": other["role"],
                "student_number": other["student_number"],
            },
            "messages": [],
        }), 200
    finally:
        conn.close()


@messages_bp.route("/api/messages", methods=["POST"])
@require_auth
def send_message_route():
    data = request.get_json(silent=True) or {}
    try:
        receiver_id = int(data.get("receiver_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "接收人参数不合法。"}), 400
    if receiver_id == g.current_user["id"]:
        return jsonify({"error": "不能给自己发送私信。"}), 400
    body_text = (data.get("body") or "").strip()
    if not body_text:
        return jsonify({"error": "消息内容不能为空。"}), 400

    conn = get_conn()
    try:
        receiver = conn.execute("SELECT id FROM users WHERE id = ?", (receiver_id,)).fetchone()
        if not receiver:
            return jsonify({"error": "接收人不存在。"}), 404
        if not users_share_class(conn, g.current_user["id"], receiver_id):
            return jsonify({"error": "仅可向同班联系人发送私信。"}), 403

        sent_message = send_message(conn, g.current_user["id"], receiver_id, body_text)
        conn.commit()
        publish_user_updates(g.current_user["id"], receiver_id)
        try:
            notify_new_message(
                receiver_id,
                g.current_user.get("display_name") or g.current_user.get("username") or "班级成员",
                body_text,
                sent_message["thread_id"],
            )
        except Exception:
            current_app.logger.exception("创建私信通知失败")
        return jsonify({
            "message": "消息发送成功。",
            "thread_id": sent_message["thread_id"],
            "sent_message": sent_message,
        }), 201
    finally:
        conn.close()


@messages_bp.route("/api/messages/conversations/<int:thread_id>", methods=["DELETE"])
@require_auth
def delete_conversation_route(thread_id: int):
    conn = get_conn()
    try:
        delete_conversation(conn, thread_id, g.current_user["id"])
        conn.commit()
        return jsonify({"message": "会话已删除。"}), 200
    finally:
        conn.close()
