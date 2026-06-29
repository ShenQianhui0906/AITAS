"""
RAG Chat Blueprint — /api/rag/*
"""
from __future__ import annotations

import json

from flask import Blueprint, request, jsonify, g

from backend.config import MAX_AI_HISTORY_MESSAGES, MODEL_NAME, STORAGE_DIR
from backend.database import get_conn
from backend.middleware.auth import require_auth
from backend.models.ai_chat import list_rag_messages, add_rag_message, clear_rag_messages
from backend.models.courseware import list_coursewares
from backend.models.access import user_can_access_class
from backend.services.ai_service import call_bigmodel_chat
from backend.services.rag_service import get_index_status
from backend.services.rag_answer_service import (
    build_knowledge_messages,
    retrieve_class_knowledge,
)

rag_bp = Blueprint("rag", __name__)

@rag_bp.route("/api/rag/status", methods=["GET"])
@require_auth
def rag_status():
    try:
        class_id = int(request.args.get("class_id", ""))
    except (TypeError, ValueError):
        return jsonify({"error": "班级编号不合法。"}), 400

    status = get_index_status(class_id)
    return jsonify({
        "status": "ready" if status.get("indexed") else "not_built",
        "building": status.get("building", False),
        "chunk_count": status.get("chunk_count", 0),
        "error": status.get("error"),
        "model_name": MODEL_NAME,
    }), 200


@rag_bp.route("/api/rag/index", methods=["POST"])
@require_auth
def build_rag_index():
    data = request.get_json(silent=True) or {}
    try:
        class_id = int(data.get("class_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "班级编号不合法。"}), 400

    conn = get_conn()
    try:
        if not user_can_access_class(conn, g.current_user, class_id):
            return jsonify({"error": "当前账号无权访问该班级。"}), 403

        coursewares = list_coursewares(conn, "c.class_id = ?", [class_id], lambda fn, title: "")
        if not coursewares:
            return jsonify({"error": "该班级暂无课件，无法构建索引。"}), 400

        from backend.services.rag_service import build_class_index_async
        from backend.services.text_service import extract_courseware_text

        upload_dir = STORAGE_DIR / "uploads"
        build_class_index_async(class_id, coursewares, upload_dir, extract_courseware_text)
        return jsonify({"message": "索引构建任务已启动。"}), 200
    finally:
        conn.close()


@rag_bp.route("/api/rag/messages", methods=["GET"])
@require_auth
def get_rag_messages():
    try:
        class_id = int(request.args.get("class_id", ""))
    except (TypeError, ValueError):
        return jsonify({"error": "班级编号不合法。"}), 400

    conn = get_conn()
    try:
        if not user_can_access_class(conn, g.current_user, class_id):
            return jsonify({"error": "当前账号无权查看班级。"}), 403
        messages = list_rag_messages(conn, class_id, g.current_user["id"])
        return jsonify({"messages": messages}), 200
    finally:
        conn.close()


@rag_bp.route("/api/rag/ask", methods=["POST"])
@require_auth
def rag_ask():
    data = request.get_json(silent=True) or {}
    try:
        class_id = int(data.get("class_id"))
        user_message = (data.get("question") or "").strip()
    except (TypeError, ValueError):
        return jsonify({"error": "请求参数不合法。"}), 400
    if not user_message:
        return jsonify({"error": "请输入问题。"}), 400

    conn = get_conn()
    try:
        if not user_can_access_class(conn, g.current_user, class_id):
            return jsonify({"error": "当前账号无权访问该班级。"}), 403

        retrieval = retrieve_class_knowledge(conn, class_id, user_message)
        related_coursewares = retrieval["related_coursewares"]
        message_sources = retrieval["sources"]

        history = list_rag_messages(conn, class_id, g.current_user["id"])
        recent = history[-MAX_AI_HISTORY_MESSAGES:] if len(history) > MAX_AI_HISTORY_MESSAGES else history

        messages = build_knowledge_messages(
            user_message, retrieval["knowledge_text"], recent
        )

        reply_text = call_bigmodel_chat(messages)

        # Store message source info. When retrieval finds no courseware, keep an explicit model-source note.
        sources_json = json.dumps(message_sources, ensure_ascii=False)
        add_rag_message(conn, class_id, g.current_user["id"], "user", user_message)
        add_rag_message(
            conn, class_id, g.current_user["id"], "assistant", reply_text,
            sources_json,
        )
        conn.commit()

        updated_messages = list_rag_messages(conn, class_id, g.current_user["id"])
        return jsonify({
            "reply": reply_text,
            "sources": message_sources,
            "related_coursewares": related_coursewares,
            "messages": updated_messages,
            "retriever_error": retrieval["retriever_error"],
        }), 200
    finally:
        conn.close()


@rag_bp.route("/api/rag/messages", methods=["DELETE"])
@require_auth
def clear_rag_messages_route():
    try:
        class_id = int(request.args.get("class_id", ""))
    except (TypeError, ValueError):
        return jsonify({"error": "班级编号不合法。"}), 400
    conn = get_conn()
    try:
        if not user_can_access_class(conn, g.current_user, class_id):
            return jsonify({"error": "当前账号无权访问该班级。"}), 403
        clear_rag_messages(conn, class_id, g.current_user["id"])
        conn.commit()
        return jsonify({"message": "对话已清空。"}), 200
    finally:
        conn.close()
