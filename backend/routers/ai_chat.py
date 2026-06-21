"""
AI Chat router — /api/ai/chat
"""
from __future__ import annotations

import json
import re
import time
from http import HTTPStatus

from backend.config import MAX_AI_CONTEXT_CHARS, MAX_AI_HISTORY_MESSAGES
from backend.database import get_conn
from backend.middleware.auth import require_user_from_header
from backend.models.ai_chat import list_ai_messages, add_ai_message, clear_ai_messages
from backend.models.courseware import get_courseware_detail
from backend.models.access import user_can_access_class
from backend.services.ai_service import call_bigmodel_chat
from backend.services.text_service import extract_courseware_text, crop_ai_context


def _build_viewer_url(file_name: str, display_title: str = "") -> str:
    from urllib.parse import quote
    import re as _re
    from pathlib import Path as _P
    name = display_title or file_name
    name = _re.sub(r'[\\/:*?"<>|]+', " ", name).strip()
    return f"/preview/{quote(file_name)}/{quote(name)}"


def handle_ai_chat_routes(path: str, method: str, headers: dict, body: bytes, query_params: dict) -> tuple[dict | list, int] | None:
    if not path.startswith("/api/ai"):
        return None
    user, error = require_user_from_header(headers.get("Authorization"))
    if error:
        return {"error": error}, HTTPStatus.UNAUTHORIZED

    # GET /api/ai/messages
    if method == "GET" and path == "/api/ai/messages":
        try:
            courseware_id = int(query_params.get("courseware_id", [""])[0])
        except (ValueError, TypeError):
            return {"error": "课件编号不合法。"}, HTTPStatus.BAD_REQUEST

        conn = get_conn()
        try:
            courseware = conn.execute(
                "SELECT cw.class_id, cw.stored_file_name, cw.title FROM coursewares cw WHERE cw.id = ?",
                (courseware_id,),
            ).fetchone()
            if not courseware:
                return {"error": "课件不存在。"}, HTTPStatus.NOT_FOUND
            if not user_can_access_class(conn, user, courseware["class_id"]):
                return {"error": "当前账号无权查看该课件。"}, HTTPStatus.FORBIDDEN
            messages = list_ai_messages(conn, user["id"], courseware_id)
            return {
                "messages": messages,
                "courseware_title": courseware["title"],
            }, HTTPStatus.OK
        finally:
            conn.close()

    # POST /api/ai/chat
    if method == "POST" and path == "/api/ai/chat":
        data = json.loads(body) if body else {}
        try:
            courseware_id = int(data.get("courseware_id"))
            user_message = (data.get("message") or "").strip()
        except (TypeError, ValueError):
            return {"error": "请求参数不合法。"}, HTTPStatus.BAD_REQUEST
        if not user_message:
            return {"error": "请输入问题。"}, HTTPStatus.BAD_REQUEST

        conn = get_conn()
        try:
            courseware = conn.execute(
                "SELECT cw.class_id, cw.stored_file_name, cw.title, cw.original_filename "
                "FROM coursewares cw WHERE cw.id = ?",
                (courseware_id,),
            ).fetchone()
            if not courseware:
                return {"error": "课件不存在。"}, HTTPStatus.NOT_FOUND
            if not user_can_access_class(conn, user, courseware["class_id"]):
                return {"error": "当前账号无权访问该课件。"}, HTTPStatus.FORBIDDEN

            # Extract courseware text
            from pathlib import Path as _P
            from backend.config import UPLOAD_DIR

            file_path = _P(UPLOAD_DIR) / "coursewares" / str(courseware_id) / "original" / courseware["stored_file_name"]
            courseware_text = extract_courseware_text(str(file_path)) if file_path.exists() else ""
            courseware_text = crop_ai_context(courseware_text, MAX_AI_CONTEXT_CHARS)

            # Build messages for AI
            history = list_ai_messages(conn, user["id"], courseware_id)
            recent = history[-MAX_AI_HISTORY_MESSAGES:] if len(history) > MAX_AI_HISTORY_MESSAGES else history

            system_prompt = (
                "你是AITAS（AI教学助手），专为课堂课件提供智能化支持。"
                "请根据以下课件内容回答学生的问题，保持专业、准确、有教育意义。"
                "如果课件中没有相关信息，请诚实告知。\n\n"
                f"【课件内容】\n{courseware_text}"
            )
            messages = [{"role": "system", "content": system_prompt}]
            for msg in recent:
                role = "assistant" if msg["role"] == "assistant" else "user"
                messages.append({"role": role, "content": msg["content"]})
            messages.append({"role": "user", "content": user_message})

            # Call AI
            reply_text = call_bigmodel_chat(messages)

            # Save messages
            add_ai_message(conn, user["id"], courseware_id, "user", user_message)
            add_ai_message(conn, user["id"], courseware_id, "assistant", reply_text)
            conn.commit()

            return {
                "reply": reply_text,
                "courseware_title": courseware["title"],
            }, HTTPStatus.OK
        finally:
            conn.close()

    # DELETE /api/ai/messages
    if method == "DELETE" and path == "/api/ai/messages":
        try:
            courseware_id = int(query_params.get("courseware_id", [""])[0])
        except (ValueError, TypeError):
            return {"error": "课件编号不合法。"}, HTTPStatus.BAD_REQUEST
        conn = get_conn()
        try:
            clear_ai_messages(conn, user["id"], courseware_id)
            conn.commit()
            return {"message": "对话已清空。"}, HTTPStatus.OK
        finally:
            conn.close()

    return None
