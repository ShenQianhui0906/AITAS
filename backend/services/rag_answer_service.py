"""Shared helpers for answers grounded in a class knowledge base."""
from __future__ import annotations

from urllib.parse import quote

from backend.config import MAX_AI_CONTEXT_CHARS
from backend.services.rag_service import query_class_index


MODEL_GENERATED_SOURCE = {
    "type": "model_generated",
    "label": "知识库中未记录相关问题，该回答为大模型生成",
}


def _build_courseware_viewer_url(stored_file_name: str, title: str) -> str:
    safe_name = quote(stored_file_name, safe="")
    safe_title = quote(title or "课件", safe="")
    return f"/preview/{safe_name}/{safe_title}"


def _build_related_coursewares(conn, chunks: list[dict]) -> list[dict]:
    seen_ids: set[int] = set()
    related: list[dict] = []
    for chunk in chunks:
        courseware_id = chunk.get("courseware_id")
        if not courseware_id or courseware_id in seen_ids:
            continue
        seen_ids.add(courseware_id)
        row = conn.execute(
            "SELECT id, title, course_name, stored_file_name FROM coursewares WHERE id = ?",
            (courseware_id,),
        ).fetchone()
        if not row:
            continue
        display_title = row["title"] or row["course_name"] or "课件"
        related.append({
            "courseware_id": row["id"],
            "title": row["title"],
            "course_name": row["course_name"],
            "viewer_url": _build_courseware_viewer_url(
                row["stored_file_name"], display_title
            ),
        })
    return related


def _dedupe_source_labels(chunks: list[dict]) -> list[str]:
    seen: set[str] = set()
    labels: list[str] = []
    for chunk in chunks:
        label = (chunk.get("source") or "").strip()
        if label and label not in seen:
            seen.add(label)
            labels.append(label)
    return labels


def retrieve_class_knowledge(conn, class_id: int, question: str) -> dict:
    """Retrieve class chunks and return the same source shape used by RAG chat."""
    chunks: list[dict] = []
    retriever_error = ""
    try:
        chunks = query_class_index(class_id, question)
    except Exception as exc:  # Retrieval failure should not prevent an LLM answer.
        retriever_error = str(exc)

    related_coursewares = _build_related_coursewares(conn, chunks)
    source_labels = _dedupe_source_labels(chunks)
    sources = related_coursewares or source_labels or [MODEL_GENERATED_SOURCE]
    knowledge_text = "\n\n".join(
        chunk.get("content", "") for chunk in chunks if chunk.get("content")
    )
    return {
        "knowledge_text": knowledge_text[:MAX_AI_CONTEXT_CHARS],
        "sources": sources,
        "related_coursewares": related_coursewares,
        "retriever_error": retriever_error or None,
    }


def build_knowledge_messages(
    question: str,
    knowledge_text: str,
    history: list[dict] | None = None,
) -> list[dict]:
    """Build the prompt shared by the knowledge-base page and homepage agent."""
    system_prompt = (
        "你是AITAS（AI教学助手），专为课堂提供智能化知识检索支持。"
        "请根据以下知识库内容回答学生的问题。如果知识库中没有相关信息，"
        "请根据你的知识诚实作答，并标注信息来源。\n"
    )
    if knowledge_text:
        system_prompt += f"\n【知识库内容】\n{knowledge_text}"

    messages = [{"role": "system", "content": system_prompt}]
    for message in history or []:
        role = "assistant" if message.get("role") == "assistant" else "user"
        messages.append({"role": role, "content": message.get("content", "")})
    messages.append({"role": "user", "content": question})
    return messages
