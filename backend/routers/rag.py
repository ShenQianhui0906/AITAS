"""
RAG Chat router — /api/rag/*
"""
from __future__ import annotations

import json
from http import HTTPStatus
from pathlib import Path

from backend.config import MAX_AI_CONTEXT_CHARS, MAX_AI_HISTORY_MESSAGES, STORAGE_DIR
from backend.database import get_conn
from backend.middleware.auth import require_user_from_header
from backend.models.ai_chat import list_rag_messages, add_rag_message, clear_rag_messages
from backend.models.courseware import list_coursewares
from backend.models.access import user_can_access_class
from backend.services.ai_service import call_bigmodel_chat


def _query_rag(collection, query_text: str, n_results: int = 4):
    """Query ChromaDB collection and return relevant chunks."""
    try:
        results = collection.query(query_texts=[query_text], n_results=n_results)
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        return [
            {"content": doc, "source": (meta.get("source", "") if meta else "")}
            for doc, meta in zip(docs, metas)
        ]
    except Exception:
        return []


def handle_rag_routes(path: str, method: str, headers: dict, body: bytes, query_params: dict) -> tuple[dict | list, int] | None:
    if not path.startswith("/api/rag"):
        return None
    user, error = require_user_from_header(headers.get("Authorization"))
    if error:
        return {"error": error}, HTTPStatus.UNAUTHORIZED

    # GET /api/rag/status
    if method == "GET" and path == "/api/rag/status":
        try:
            class_id = int(query_params.get("class_id", [""])[0])
        except (ValueError, TypeError):
            return {"error": "班级编号不合法。"}, HTTPStatus.BAD_REQUEST
        from rag import get_index_status
        status = get_index_status(class_id)
        return {
            "status": "ready" if status.get("indexed") else "not_built",
            "building": status.get("building", False),
            "chunk_count": status.get("chunk_count", 0),
            "error": status.get("error"),
        }, HTTPStatus.OK

    # POST /api/rag/index
    if method == "POST" and path == "/api/rag/index":
        data = json.loads(body) if body else {}
        try:
            class_id = int(data.get("class_id"))
        except (TypeError, ValueError):
            return {"error": "班级编号不合法。"}, HTTPStatus.BAD_REQUEST

        conn = get_conn()
        try:
            if not user_can_access_class(conn, user, class_id):
                return {"error": "当前账号无权访问该班级。"}, HTTPStatus.FORBIDDEN

            coursewares = list_coursewares(conn, "c.class_id = ?", [class_id], lambda fn, title: "")
            if not coursewares:
                return {"error": "该班级暂无课件，无法构建索引。"}, HTTPStatus.BAD_REQUEST

            from rag import build_class_index_async
            from backend.services.text_service import extract_courseware_text

            upload_dir = STORAGE_DIR / "uploads" / "coursewares" / str(class_id) / "original"
            build_class_index_async(class_id, coursewares, upload_dir, extract_courseware_text)
            return {"message": "索引构建任务已启动。"}, HTTPStatus.OK
        finally:
            conn.close()

    # GET /api/rag/messages
    if method == "GET" and path == "/api/rag/messages":
        try:
            class_id = int(query_params.get("class_id", [""])[0])
        except (ValueError, TypeError):
            return {"error": "班级编号不合法。"}, HTTPStatus.BAD_REQUEST

        conn = get_conn()
        try:
            if not user_can_access_class(conn, user, class_id):
                return {"error": "当前账号无权查看班级。"}, HTTPStatus.FORBIDDEN
            messages = list_rag_messages(conn, user["id"], class_id)
            return {"messages": messages}, HTTPStatus.OK
        finally:
            conn.close()

    # POST /api/rag/ask
    if method == "POST" and path == "/api/rag/ask":
        data = json.loads(body) if body else {}
        try:
            class_id = int(data.get("class_id"))
            user_message = (data.get("question") or "").strip()
        except (TypeError, ValueError):
            return {"error": "请求参数不合法。"}, HTTPStatus.BAD_REQUEST
        if not user_message:
            return {"error": "请输入问题。"}, HTTPStatus.BAD_REQUEST

        conn = get_conn()
        try:
            if not user_can_access_class(conn, user, class_id):
                return {"error": "当前账号无权访问该班级。"}, HTTPStatus.FORBIDDEN

            # Try ChromaDB RAG
            sources = []
            knowledge_text = ""
            try:
                from backend.config import CHROMA_DIR
                import chromadb

                client = chromadb.PersistentClient(path=str(CHROMA_DIR))
                collection_name = f"class_{class_id}"
                try:
                    collection = client.get_collection(collection_name)
                except Exception:
                    collection = None

                if collection:
                    chunks = _query_rag(collection, user_message)
                    knowledge_text = "\n\n".join(c["content"] for c in chunks)
                    sources = [c["source"] for c in chunks if c["source"]]
            except Exception:
                pass

            # Build messages for AI
            history = list_rag_messages(conn, user["id"], class_id)
            recent = history[:-1] if len(history) > MAX_AI_HISTORY_MESSAGES else history

            system_prompt = (
                "你是AITAS（AI教学助手），专为课堂提供智能化知识检索支持。"
                "请根据以下知识库内容回答学生的问题。如果知识库中没有相关信息，"
                "请根据你的知识诚实作答，并标注信息来源。\n"
            )
            if knowledge_text:
                system_prompt += f"\n【知识库内容】\n{knowledge_text[:MAX_AI_CONTEXT_CHARS]}"

            messages = [{"role": "system", "content": system_prompt}]
            for msg in recent:
                role = "assistant" if msg["role"] == "assistant" else "user"
                messages.append({"role": role, "content": msg["content"]})
            messages.append({"role": "user", "content": user_message})

            # Call AI
            reply_text = call_bigmodel_chat(messages)

            # Save messages
            add_rag_message(conn, user["id"], class_id, "user", user_message)
            add_rag_message(
                conn, user["id"], class_id, "assistant", reply_text,
                json.dumps(sources, ensure_ascii=False) if sources else None,
            )
            conn.commit()

            # Return full message list so frontend can display
            updated_messages = list_rag_messages(conn, user["id"], class_id)
            return {"reply": reply_text, "sources": sources, "messages": updated_messages}, HTTPStatus.OK
        finally:
            conn.close()

    # DELETE /api/rag/messages
    if method == "DELETE" and path == "/api/rag/messages":
        try:
            class_id = int(query_params.get("class_id", [""])[0])
        except (ValueError, TypeError):
            return {"error": "班级编号不合法。"}, HTTPStatus.BAD_REQUEST
        conn = get_conn()
        try:
            clear_rag_messages(conn, user["id"], class_id)
            conn.commit()
            return {"message": "对话已清空。"}, HTTPStatus.OK
        finally:
            conn.close()

    return None
