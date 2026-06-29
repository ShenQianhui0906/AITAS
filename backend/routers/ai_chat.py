"""
AI Chat Blueprint — /api/ai/chat
"""
from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from flask import Blueprint, request, jsonify, g

from backend.config import MAX_AI_CONTEXT_CHARS, MAX_AI_HISTORY_MESSAGES, UPLOAD_DIR
from backend.database import get_conn
from backend.middleware.auth import require_auth
from backend.models.ai_chat import list_ai_messages, add_ai_message, clear_ai_messages
from backend.models.access import user_can_access_class
from backend.services.ai_service import call_bigmodel_chat
from backend.services.text_service import extract_courseware_text, crop_ai_context

ai_chat_bp = Blueprint("ai_chat", __name__)


@ai_chat_bp.route("/api/ai/messages", methods=["GET"])
@require_auth
def get_ai_messages():
    try:
        courseware_id = int(request.args.get("courseware_id", ""))
    except (TypeError, ValueError):
        return jsonify({"error": "课件编号不合法。"}), 400

    conn = get_conn()
    try:
        courseware = conn.execute(
            "SELECT cw.class_id, cw.stored_file_name, cw.title FROM coursewares cw WHERE cw.id = ?",
            (courseware_id,),
        ).fetchone()
        if not courseware:
            return jsonify({"error": "课件不存在。"}), 404
        if not user_can_access_class(conn, g.current_user, courseware["class_id"]):
            return jsonify({"error": "当前账号无权查看该课件。"}), 403
        messages = list_ai_messages(conn, courseware_id, g.current_user["id"])
        return jsonify({
            "messages": messages,
            "courseware_title": courseware["title"],
        }), 200
    finally:
        conn.close()


@ai_chat_bp.route("/api/ai/chat", methods=["POST"])
@require_auth
def ai_chat():
    data = request.get_json(silent=True) or {}
    try:
        courseware_id = int(data.get("courseware_id"))
        user_message = (data.get("message") or "").strip()
    except (TypeError, ValueError):
        return jsonify({"error": "请求参数不合法。"}), 400
    if not user_message:
        return jsonify({"error": "请输入问题。"}), 400

    conn = get_conn()
    try:
        courseware = conn.execute(
            "SELECT cw.class_id, cw.stored_file_name, cw.title, cw.original_file_name "
            "FROM coursewares cw WHERE cw.id = ?",
            (courseware_id,),
        ).fetchone()
        if not courseware:
            return jsonify({"error": "课件不存在。"}), 404
        if not user_can_access_class(conn, g.current_user, courseware["class_id"]):
            return jsonify({"error": "当前账号无权访问该课件。"}), 403

        file_path = UPLOAD_DIR / "coursewares" / str(courseware_id) / "original" / courseware["stored_file_name"].split("/")[-1]
        courseware_text = extract_courseware_text(str(file_path)) if file_path.exists() else ""
        courseware_text = crop_ai_context(courseware_text, MAX_AI_CONTEXT_CHARS)

        history = list_ai_messages(conn, courseware_id, g.current_user["id"])
        recent = history[-MAX_AI_HISTORY_MESSAGES:] if len(history) > MAX_AI_HISTORY_MESSAGES else history

        system_prompt = (
            "你是AITAS（AI教学助手），专为课堂课件提供智能化支持。"
            "请根据以下课件内容回答学生的问题，保持专业、准确、有教育意义。"
            "如果课件中没有相关信息，请诚实告知。\n\n"
            f"【课件内容】\n{courseware_text}"
        )
        msgs = [{"role": "system", "content": system_prompt}]
        for msg in recent:
            role = "assistant" if msg["role"] == "assistant" else "user"
            msgs.append({"role": role, "content": msg["content"]})
        msgs.append({"role": "user", "content": user_message})

        reply_text = call_bigmodel_chat(msgs)

        add_ai_message(conn, courseware_id, g.current_user["id"], "user", user_message)
        add_ai_message(conn, courseware_id, g.current_user["id"], "assistant", reply_text)
        conn.commit()

        return jsonify({
            "reply": reply_text,
            "courseware_title": courseware["title"],
        }), 200
    finally:
        conn.close()


@ai_chat_bp.route("/api/ai/messages", methods=["DELETE"])
@require_auth
def delete_ai_messages():
    try:
        courseware_id = int(request.args.get("courseware_id", ""))
    except (TypeError, ValueError):
        return jsonify({"error": "课件编号不合法。"}), 400
    conn = get_conn()
    try:
        clear_ai_messages(conn, courseware_id, g.current_user["id"])
        conn.commit()
        return jsonify({"message": "对话已清空。"}), 200
    finally:
        conn.close()
