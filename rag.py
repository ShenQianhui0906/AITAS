"""
RAG (Retrieval-Augmented Generation) module for AITAS.

Uses LangChain + ChromaDB + HuggingFace sentence-transformers to build a
per-class vector index over all courseware files, then answers questions
by retrieving the most relevant chunks and passing them to the LLM.
"""

from __future__ import annotations

import json
import os
import re
import threading
from pathlib import Path
from typing import Callable, Optional

# ---------------------------------------------------------------------------
# Lazy-loaded heavy dependencies (imported once on first use)
# ---------------------------------------------------------------------------
_embeddings_instance = None
_embeddings_lock = threading.Lock()

_chroma_client = None
_chroma_lock = threading.Lock()


def _get_chroma_dir() -> Path:
    root = Path(__file__).resolve().parent
    chroma_dir = root / "data" / "chroma"
    chroma_dir.mkdir(parents=True, exist_ok=True)
    return chroma_dir


def _get_embeddings():
    """Return a shared HuggingFace embedding model (thread-safe, loaded once)."""
    global _embeddings_instance
    if _embeddings_instance is None:
        with _embeddings_lock:
            if _embeddings_instance is None:
                from langchain_community.embeddings import HuggingFaceEmbeddings

                model_name = os.environ.get(
                    "EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2"
                )
                _embeddings_instance = HuggingFaceEmbeddings(
                    model_name=model_name,
                    model_kwargs={"device": "cpu"},
                    encode_kwargs={"normalize_embeddings": True},
                )
    return _embeddings_instance


def _get_chroma_client():
    """Return a shared persistent ChromaDB client (thread-safe, created once)."""
    global _chroma_client
    if _chroma_client is None:
        with _chroma_lock:
            if _chroma_client is None:
                import chromadb

                _chroma_client = chromadb.PersistentClient(path=str(_get_chroma_dir()))
    return _chroma_client


def _collection_name(class_id: int) -> str:
    return f"class_{class_id}"


# ---------------------------------------------------------------------------
# Index status tracking (in-memory, per class)
# ---------------------------------------------------------------------------
_index_status: dict[int, dict] = {}
_status_lock = threading.Lock()


def _set_status(class_id: int, **kwargs):
    with _status_lock:
        current = _index_status.get(class_id, {})
        current.update(kwargs)
        _index_status[class_id] = current


def get_index_status(class_id: int) -> dict:
    """
    Returns:
        {
            "building": bool,
            "indexed": bool,
            "chunk_count": int,
            "error": str | None,
        }
    """
    with _status_lock:
        base = _index_status.get(class_id, {}).copy()

    building = base.get("building", False)
    error = base.get("error")

    # Check actual collection count from ChromaDB
    chunk_count = 0
    indexed = False
    try:
        client = _get_chroma_client()
        col = client.get_or_create_collection(_collection_name(class_id))
        chunk_count = col.count()
        indexed = chunk_count > 0
    except Exception:
        pass

    return {
        "building": building,
        "indexed": indexed,
        "chunk_count": chunk_count,
        "error": error,
    }


# ---------------------------------------------------------------------------
# Text splitting
# ---------------------------------------------------------------------------

def _split_text(text: str, chunk_size: int = 500, overlap: int = 80) -> list[str]:
    """
    Split *text* into overlapping chunks of roughly *chunk_size* characters.

    Strategy:
    1. Split by double-newlines (paragraph boundaries).
    2. Merge short paragraphs until close to chunk_size.
    3. If a single paragraph is still too long, hard-split it.
    """
    if not text.strip():
        return []

    # Normalise line endings and collapse runs of blank lines
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    raw_chunks: list[str] = []
    for para in paragraphs:
        if len(para) <= chunk_size:
            raw_chunks.append(para)
        else:
            # Hard-split long paragraphs at sentence boundaries first
            sentences = re.split(r"(?<=[。！？.!?\n])", para)
            buf = ""
            for sent in sentences:
                if not sent.strip():
                    continue
                if len(buf) + len(sent) > chunk_size and buf:
                    raw_chunks.append(buf.strip())
                    buf = sent
                else:
                    buf += sent
            if buf.strip():
                raw_chunks.append(buf.strip())

    # Merge + overlap
    merged: list[str] = []
    buf = ""
    for chunk in raw_chunks:
        if len(buf) + len(chunk) + 1 <= chunk_size:
            buf = (buf + "\n" + chunk).strip() if buf else chunk
        else:
            if buf:
                merged.append(buf)
            # start next chunk with overlap from previous
            if overlap > 0 and buf:
                buf = (buf[-overlap:] + "\n" + chunk).strip()
            else:
                buf = chunk

    if buf.strip():
        merged.append(buf.strip())

    return [c for c in merged if c.strip()]


# ---------------------------------------------------------------------------
# Index building
# ---------------------------------------------------------------------------

def build_class_index_async(
    class_id: int,
    courseware_list: list[dict],
    upload_dir: Path,
    extract_fn: Callable[[Path], str],
) -> None:
    """
    Start a background thread that builds (or rebuilds) the ChromaDB index
    for *class_id* from the given courseware list.

    *courseware_list* items must have keys: id, title, course_name, stored_file_name.
    *extract_fn* accepts a Path and returns the extracted plain text.
    """
    _set_status(class_id, building=True, error=None)
    t = threading.Thread(
        target=_build_index,
        args=(class_id, courseware_list, upload_dir, extract_fn),
        daemon=True,
    )
    t.start()


def _build_index(
    class_id: int,
    courseware_list: list[dict],
    upload_dir: Path,
    extract_fn: Callable[[Path], str],
) -> None:
    try:
        embeddings = _get_embeddings()
        client = _get_chroma_client()
        col_name = _collection_name(class_id)

        # Drop existing collection and recreate
        try:
            client.delete_collection(col_name)
        except Exception:
            pass
        col = client.create_collection(
            col_name,
            metadata={"hnsw:space": "cosine"},
        )

        all_texts: list[str] = []
        all_ids: list[str] = []
        all_metas: list[dict] = []

        for cw in courseware_list:
            cw_id = cw["id"]
            title = cw.get("title", "")
            course_name = cw.get("course_name", "")
            stored_name = cw.get("stored_file_name", "")
            source_label = f"{course_name} · {title}" if course_name else title

            file_path = upload_dir / stored_name
            text = extract_fn(file_path)
            if not text.strip():
                continue

            chunks = _split_text(text)
            for idx, chunk in enumerate(chunks):
                doc_id = f"cw{cw_id}_chunk{idx}"
                all_texts.append(chunk)
                all_ids.append(doc_id)
                all_metas.append(
                    {
                        "courseware_id": cw_id,
                        "title": title,
                        "course_name": course_name,
                        "chunk_index": idx,
                        "source": source_label,
                    }
                )

        if not all_texts:
            _set_status(class_id, building=False)
            return

        # Embed in batches of 64
        batch_size = 64
        for start in range(0, len(all_texts), batch_size):
            batch_texts = all_texts[start : start + batch_size]
            batch_ids = all_ids[start : start + batch_size]
            batch_metas = all_metas[start : start + batch_size]
            batch_embeddings = embeddings.embed_documents(batch_texts)
            col.add(
                ids=batch_ids,
                documents=batch_texts,
                embeddings=batch_embeddings,
                metadatas=batch_metas,
            )

        _set_status(class_id, building=False, error=None)

    except Exception as exc:  # noqa: BLE001
        _set_status(class_id, building=False, error=str(exc))


# ---------------------------------------------------------------------------
# RAG Q&A
# ---------------------------------------------------------------------------

def rag_ask(
    class_id: int,
    question: str,
    history_messages: Optional[list[dict]] = None,
    n_results: int = 5,
) -> dict:
    """
    Perform RAG Q&A for the given class.

    Returns:
        {"answer": str, "sources": [str]}
    """
    if not question.strip():
        return {"answer": "请输入问题。", "sources": []}

    # ---- retrieve relevant chunks ----------------------------------------
    embeddings = _get_embeddings()
    client = _get_chroma_client()
    col_name = _collection_name(class_id)

    try:
        col = client.get_collection(col_name)
    except Exception:
        return {
            "answer": "当前班级尚未建立知识库索引，请先由教师点击[建立索引]。",
            "sources": [],
        }

    if col.count() == 0:
        return {
            "answer": "知识库索引为空，请先由教师点击[建立索引]重新构建。",
            "sources": [],
        }

    q_embedding = embeddings.embed_query(question)
    results = col.query(
        query_embeddings=[q_embedding],
        n_results=min(n_results, col.count()),
        include=["documents", "metadatas"],
    )

    docs: list[str] = results.get("documents", [[]])[0]
    metas: list[dict] = results.get("metadatas", [[]])[0]

    if not docs:
        return {
            "answer": "未能从知识库中检索到相关内容，请尝试换一种表述方式。",
            "sources": [],
        }

    # Deduplicate sources
    seen_sources: set[str] = set()
    sources: list[str] = []
    for meta in metas:
        src = meta.get("source", "")
        if src and src not in seen_sources:
            seen_sources.add(src)
            sources.append(src)

    context = "\n\n---\n\n".join(docs)

    # ---- build LLM messages ----------------------------------------------
    system_prompt = (
        "你是一名高校课程 AI 助教，负责基于提供的课件知识库内容回答学生问题。\n"
        "请使用简洁、准确、友好的中文回答。\n"
        "优先依据下方检索到的课件片段作答；如果片段中没有相关信息，请明确说明，不要编造。\n"
        "回答结构清晰，优先使用 Markdown 格式（标题、列表等）。\n"
        "先给出一句简短结论，再用 2~4 个段落展开说明。"
    )

    context_prompt = (
        f"以下是从课件知识库中检索到的相关片段：\n\n{context}"
    )

    history = history_messages or []
    llm_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": context_prompt},
        *history,
        {"role": "user", "content": question},
    ]

    # ---- call LLM --------------------------------------------------------
    api_url = os.environ.get(
        "BIGMODEL_API_URL", "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    ).strip()
    api_key = os.environ.get("BIGMODEL_API_KEY", "").strip()
    model = os.environ.get("BIGMODEL_MODEL", "glm-4.7-flash").strip()

    if not api_key:
        raise RuntimeError("BIGMODEL_API_KEY 未配置，无法调用 AI 服务。")

    import urllib.request as _req
    import urllib.error as _err

    payload = json.dumps(
        {"model": model, "messages": llm_messages, "stream": False},
        ensure_ascii=False,
    ).encode("utf-8")

    request = _req.Request(
        api_url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with _req.urlopen(request, timeout=60) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except _err.HTTPError as exc:
        raise RuntimeError(f"AI 服务请求失败 (HTTP {exc.code})：{exc.reason}") from exc
    except Exception as exc:
        raise RuntimeError(f"AI 服务暂时不可用：{exc}") from exc

    answer = ""
    choices = body.get("choices") or []
    if choices:
        msg = choices[0].get("message") or {}
        content = msg.get("content") or ""
        if isinstance(content, str):
            answer = content.strip()
        elif isinstance(content, list):
            parts = [
                item.get("text", "") if isinstance(item, dict) else str(item)
                for item in content
            ]
            answer = "\n".join(p for p in parts if p).strip()

    if not answer:
        raise RuntimeError("AI 服务返回了空响应，请稍后重试。")

    return {"answer": answer, "sources": sources}
