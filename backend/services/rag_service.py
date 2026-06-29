"""
RAG (Retrieval-Augmented Generation) service for AITAS.

Uses LangChain + ChromaDB + HuggingFace sentence-transformers to build a
per-class vector index over all courseware files.

Moved from root-level rag.py into the backend package.
"""
from __future__ import annotations

import json
import os
import re
import threading
from pathlib import Path
from typing import Callable

from backend.config import CHROMA_DIR, PROCESSED_DIR

# ---------------------------------------------------------------------------
# Lazy-loaded heavy dependencies (imported once on first use)
# ---------------------------------------------------------------------------
_embeddings_instance = None
_embeddings_lock = threading.Lock()

_chroma_client = None
_chroma_lock = threading.Lock()

LEXICAL_MIN_SCORE = 4.0
QUERY_STOP_PHRASES = (
    "怎么样",
    "是什么",
    "有什么",
    "有哪些",
    "为什么",
    "怎么",
    "如何",
    "请问",
    "介绍一下",
    "解释一下",
    "说明一下",
    "总结一下",
    "什么",
    "哪些",
)
QUERY_STOP_TOKENS = {
    "这个",
    "那个",
    "一下",
    "请",
    "是",
    "吗",
    "呢",
    "吧",
    "的",
}


def _get_chroma_dir() -> Path:
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return CHROMA_DIR


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


def _lexical_index_dir() -> Path:
    index_dir = PROCESSED_DIR / "rag_indexes"
    index_dir.mkdir(parents=True, exist_ok=True)
    return index_dir


def _lexical_index_path(class_id: int) -> Path:
    return _lexical_index_dir() / f"class_{class_id}.json"


def get_collection(class_id: int):
    """
    Return the ChromaDB collection for *class_id* with the **same**
    HuggingFace embedding function used during index building.

    This ensures query embeddings and stored embeddings are in the
    same vector space — fixing the embedding-model mismatch between
    index (HuggingFace) and query (ChromaDB built-in default).
    """
    client = _get_chroma_client()
    embeddings = _get_embeddings()
    return client.get_or_create_collection(
        _collection_name(class_id),
        embedding_function=embeddings,
        metadata={"hnsw:space": "cosine"},
    )


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

    # Check actual collection count from ChromaDB, then fall back to the
    # lightweight lexical index when vector dependencies are unavailable.
    chunk_count = 0
    indexed = False
    try:
        col = get_collection(class_id)
        chunk_count = col.count()
        indexed = chunk_count > 0
    except Exception:
        pass

    if not indexed:
        lexical = _load_lexical_index(class_id)
        chunk_count = len(lexical.get("chunks", []))
        indexed = chunk_count > 0

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


def _extract_index_chunks(
    courseware_list: list[dict],
    upload_dir: Path,
    extract_fn: Callable[[Path], str],
) -> tuple[list[str], list[str], list[dict]]:
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

    return all_texts, all_ids, all_metas


def _write_lexical_index(class_id: int, texts: list[str], ids: list[str], metas: list[dict]) -> None:
    chunks = [
        {"id": doc_id, "content": text, "metadata": meta}
        for doc_id, text, meta in zip(ids, texts, metas)
    ]
    payload = {"class_id": class_id, "chunks": chunks}
    _lexical_index_path(class_id).write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )


def _load_lexical_index(class_id: int) -> dict:
    index_path = _lexical_index_path(class_id)
    if not index_path.exists():
        return {"class_id": class_id, "chunks": []}
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"class_id": class_id, "chunks": []}
    if not isinstance(payload, dict) or not isinstance(payload.get("chunks"), list):
        return {"class_id": class_id, "chunks": []}
    return payload


def _normalize_query_for_lexical_search(text: str) -> str:
    text = (text or "").lower()
    for phrase in QUERY_STOP_PHRASES:
        text = text.replace(phrase, " ")
    for token in QUERY_STOP_TOKENS:
        text = text.replace(token, " ")
    text = re.sub(r"[^\w\u4e00-\u9fff]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _query_tokens(text: str) -> set[str]:
    text = _normalize_query_for_lexical_search(text)
    tokens = set(re.findall(r"[a-z0-9_]{2,}", text))

    for seq in re.findall(r"[\u4e00-\u9fff]{2,}", text):
        tokens.add(seq)
        for size in (2, 3, 4):
            if len(seq) >= size:
                tokens.update(seq[i : i + size] for i in range(len(seq) - size + 1))

    return {t for t in tokens if t.strip() and t not in QUERY_STOP_TOKENS}


def _primary_query_tokens(text: str) -> set[str]:
    text = _normalize_query_for_lexical_search(text)
    tokens = set(re.findall(r"[a-z0-9_]{2,}", text))
    tokens.update(re.findall(r"[\u4e00-\u9fff]{2,}", text))
    return {t for t in tokens if t.strip() and t not in QUERY_STOP_TOKENS}


def _chunk_search_text(chunk: dict) -> str:
    content = str(chunk.get("content") or "").lower()
    meta = chunk.get("metadata") if isinstance(chunk.get("metadata"), dict) else {}
    source_text = " ".join(
        str(meta.get(key) or "").lower()
        for key in ("title", "course_name", "source")
    )
    return f"{content}\n{source_text}"


def _matches_primary_query_tokens(chunk: dict, primary_tokens: set[str]) -> bool:
    if not primary_tokens:
        return True
    haystack = _chunk_search_text(chunk)
    return any(token in haystack for token in primary_tokens)


def _score_lexical_chunk(query_text: str, query_tokens: set[str], chunk: dict) -> float:
    meta = chunk.get("metadata") if isinstance(chunk.get("metadata"), dict) else {}
    source_text = " ".join(
        str(meta.get(key) or "").lower()
        for key in ("title", "course_name", "source")
    )
    haystack = _chunk_search_text(chunk)

    score = 0.0
    for token in query_tokens:
        occurrences = haystack.count(token)
        if not occurrences:
            continue
        token_score = 1.0 + min(len(token), 6) * 0.35
        if token in source_text:
            token_score *= 1.6
        score += token_score * min(occurrences, 6)

    normalized_query = re.sub(r"\s+", "", query_text.lower())
    if normalized_query and normalized_query in re.sub(r"\s+", "", haystack):
        score += 8.0

    return score


def query_lexical_index(class_id: int, query_text: str, n_results: int = 4) -> list[dict]:
    payload = _load_lexical_index(class_id)
    chunks = payload.get("chunks", [])
    if not chunks:
        return []

    tokens = _query_tokens(query_text)
    if not tokens:
        return []
    primary_tokens = _primary_query_tokens(query_text)

    scored = []
    for chunk in chunks:
        score = _score_lexical_chunk(query_text, tokens, chunk)
        if score >= LEXICAL_MIN_SCORE and _matches_primary_query_tokens(chunk, primary_tokens):
            scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    results = []
    for _, chunk in scored[:n_results]:
        meta = chunk.get("metadata") if isinstance(chunk.get("metadata"), dict) else {}
        results.append(
            {
                "content": chunk.get("content", ""),
                "source": meta.get("source", ""),
                "courseware_id": meta.get("courseware_id"),
            }
        )
    return results


def query_class_index(class_id: int, query_text: str, n_results: int = 4) -> list[dict]:
    try:
        collection = get_collection(class_id)
        if collection and collection.count() > 0:
            results = collection.query(query_texts=[query_text], n_results=n_results)
            docs = results.get("documents", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            chunks = [
                {
                    "content": doc,
                    "source": (meta.get("source", "") if meta else ""),
                    "courseware_id": (meta.get("courseware_id") if meta else None),
                }
                for doc, meta in zip(docs, metas)
            ]
            if chunks:
                return chunks
    except Exception:
        pass

    return query_lexical_index(class_id, query_text, n_results)


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

    *upload_dir* is the uploads root directory.
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
        all_texts, all_ids, all_metas = _extract_index_chunks(courseware_list, upload_dir, extract_fn)

        if not all_texts:
            _set_status(class_id, building=False, error="未从课件中提取到可索引文本。")
            return

        _write_lexical_index(class_id, all_texts, all_ids, all_metas)

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
                embedding_function=embeddings,
                metadata={"hnsw:space": "cosine"},
            )

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
            # 通知班级学生知识库已就绪
            _notify_index_complete(class_id)
            return
        except Exception as exc:
            _set_status(
                class_id,
                building=False,
                error=f"向量索引不可用，已启用关键词索引：{exc}",
            )
            return

    except Exception as exc:
        _set_status(class_id, building=False, error=str(exc))


def _notify_index_complete(class_id: int) -> None:
    """通知班级学生知识库索引已就绪"""
    try:
        from backend.database import get_conn
        from backend.services.notification_service import notify_courseware_indexed
        conn = get_conn()
        try:
            # 获取班级内的学生
            students = conn.execute(
                "SELECT cm.user_id FROM class_members cm JOIN users u ON cm.user_id = u.id WHERE cm.class_id = ? AND u.role = 'student'",
                (class_id,)
            ).fetchall()
            student_ids = [s[0] for s in students]
            if student_ids:
                notify_courseware_indexed(class_id, student_ids)
        finally:
            conn.close()
    except Exception:
        pass  # 通知失败不影响索引构建
