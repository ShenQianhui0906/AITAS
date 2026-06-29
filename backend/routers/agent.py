"""Homepage AI agent routes — intent routing plus persistent student history."""
from __future__ import annotations

import json

from flask import Blueprint, g, jsonify, request

from backend.config import MAX_AI_HISTORY_MESSAGES
from backend.database import get_conn
from backend.middleware.auth import require_auth
from backend.models.access import user_can_access_class
from backend.models.ai_chat import (
    add_agent_message,
    clear_agent_messages,
    list_agent_messages,
)
from backend.services.agent_service import (
    KNOWLEDGE_INTENTS,
    PERSONAL_HISTORY_SOURCE,
    build_personalized_messages,
    classify_agent_intent,
    list_historical_questions,
)
from backend.services.ai_service import call_bigmodel_chat
from backend.services.rag_answer_service import (
    build_knowledge_messages,
    retrieve_class_knowledge,
)


agent_bp = Blueprint("agent", __name__)


def _parse_class_id(raw_value) -> int | None:
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return None


def _ensure_student():
    if g.current_user["role"] != "student":
        return jsonify({"error": "首页智能助教仅面向学生使用。"}), 403
    return None


@agent_bp.route("/api/ai/agent/messages", methods=["GET"])
@require_auth
def get_agent_messages():
    role_error = _ensure_student()
    if role_error:
        return role_error
    class_id = _parse_class_id(request.args.get("class_id"))
    if not class_id:
        return jsonify({"error": "班级编号不合法。"}), 400

    conn = get_conn()
    try:
        if not user_can_access_class(conn, g.current_user, class_id):
            return jsonify({"error": "当前账号无权访问该班级。"}), 403
        return jsonify({
            "messages": list_agent_messages(conn, class_id, g.current_user["id"])
        }), 200
    finally:
        conn.close()


@agent_bp.route("/api/ai/agent", methods=["POST"])
@require_auth
def ask_agent():
    role_error = _ensure_student()
    if role_error:
        return role_error

    data = request.get_json(silent=True) or {}
    class_id = _parse_class_id(data.get("class_id"))
    question = (data.get("message") or data.get("question") or "").strip()
    if not class_id:
        return jsonify({"error": "班级编号不合法。"}), 400
    if not question:
        return jsonify({"error": "请输入问题。"}), 400

    conn = get_conn()
    try:
        if not user_can_access_class(conn, g.current_user, class_id):
            return jsonify({"error": "当前账号无权访问该班级。"}), 403

        class_row = conn.execute(
            "SELECT id, name, description FROM classes WHERE id = ?", (class_id,)
        ).fetchone()
        if not class_row:
            return jsonify({"error": "班级不存在。"}), 404

        # Intent is always recognised server-side before selecting an answer path.
        intent = classify_agent_intent(question)
        conversation = list_agent_messages(conn, class_id, g.current_user["id"])
        recent = conversation[-MAX_AI_HISTORY_MESSAGES:]
        retrieval = None

        if intent in KNOWLEDGE_INTENTS:
            route = "knowledge_base"
            retrieval = retrieve_class_knowledge(conn, class_id, question)
            llm_messages = build_knowledge_messages(
                question, retrieval["knowledge_text"], recent
            )
            sources = retrieval["sources"]
        else:
            route = "personalized"
            historical_questions = list_historical_questions(
                conn, g.current_user["id"], class_id
            )
            llm_messages = build_personalized_messages(
                question=question,
                intent=intent,
                user=g.current_user,
                class_info=dict(class_row),
                historical_questions=historical_questions,
                conversation_history=recent,
            )
            sources = [PERSONAL_HISTORY_SOURCE]

        try:
            reply_text = call_bigmodel_chat(llm_messages)
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 502

        sources_json = json.dumps(sources, ensure_ascii=False)
        add_agent_message(
            conn, class_id, g.current_user["id"], "user", question, intent
        )
        add_agent_message(
            conn,
            class_id,
            g.current_user["id"],
            "assistant",
            reply_text,
            intent,
            sources_json,
        )
        conn.commit()

        response = {
            "reply": reply_text,
            "intent": intent,
            "route": route,
            "sources": sources,
            "messages": list_agent_messages(conn, class_id, g.current_user["id"]),
        }
        if retrieval:
            response.update({
                "related_coursewares": retrieval["related_coursewares"],
                "retriever_error": retrieval["retriever_error"],
            })
        return jsonify(response), 200
    finally:
        conn.close()


@agent_bp.route("/api/ai/agent/messages", methods=["DELETE"])
@require_auth
def delete_agent_messages():
    role_error = _ensure_student()
    if role_error:
        return role_error
    class_id = _parse_class_id(request.args.get("class_id"))
    if not class_id:
        return jsonify({"error": "班级编号不合法。"}), 400

    conn = get_conn()
    try:
        if not user_can_access_class(conn, g.current_user, class_id):
            return jsonify({"error": "当前账号无权访问该班级。"}), 403
        clear_agent_messages(conn, class_id, g.current_user["id"])
        conn.commit()
        return jsonify({"message": "首页助教对话已清空。"}), 200
    finally:
        conn.close()
