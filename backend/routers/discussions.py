"""
Discussions Blueprint — /api/discussions/*
"""
from __future__ import annotations

from flask import Blueprint, request, jsonify, g

from backend.database import get_conn
from backend.middleware.auth import require_auth
from backend.models.discussion import (
    list_discussions, get_discussion_detail,
    create_discussion, create_reply,
)
from backend.models.access import build_class_scope_clause, user_can_access_class
from backend.services.sync_service import publish_user_updates

discussions_bp = Blueprint("discussions", __name__)


@discussions_bp.route("/api/discussions", methods=["GET"])
@require_auth
def get_discussions():
    conn = get_conn()
    try:
        class_id = request.args.get("class_id", type=int)
        if class_id and not user_can_access_class(conn, g.current_user, class_id):
            return jsonify({"error": "当前账号无权查看该班级讨论。"}), 403
        clause, params = build_class_scope_clause(g.current_user, class_id, "d.class_id")
        discussions = list_discussions(conn, clause, params, class_id)
        return jsonify({"discussions": discussions}), 200
    finally:
        conn.close()


@discussions_bp.route("/api/discussions", methods=["POST"])
@require_auth
def create_discussion_route():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    body_text = (data.get("body") or "").strip()
    try:
        class_id = int(data.get("class_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "请选择班级。"}), 400
    if not title or not body_text:
        return jsonify({"error": "标题和内容不能为空。"}), 400

    conn = get_conn()
    try:
        if not user_can_access_class(conn, g.current_user, class_id):
            return jsonify({"error": "当前账号无权在该班级发起讨论。"}), 403
        discussion = create_discussion(conn, title, body_text, g.current_user["id"], class_id)
        conn.commit()
        return jsonify({"discussion": discussion}), 201
    finally:
        conn.close()


@discussions_bp.route("/api/discussions/<int:discussion_id>/replies", methods=["POST"])
@require_auth
def create_reply_route(discussion_id: int):
    data = request.get_json(silent=True) or {}
    body_text = (data.get("body") or "").strip()
    if not body_text:
        return jsonify({"error": "回复内容不能为空。"}), 400

    conn = get_conn()
    try:
        discussion = get_discussion_detail(conn, discussion_id)
        if not discussion:
            return jsonify({"error": "讨论不存在。"}), 404
        if not user_can_access_class(conn, g.current_user, discussion["class_id"]):
            return jsonify({"error": "当前账号无权回复该讨论。"}), 403
        reply = create_reply(conn, discussion_id, body_text, g.current_user["id"])
        conn.commit()
        publish_user_updates(discussion["author_id"])
        return jsonify({"reply": reply}), 201
    finally:
        conn.close()

