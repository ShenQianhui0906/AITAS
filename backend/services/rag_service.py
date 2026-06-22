"""
RAG (Retrieval-Augmented Generation) service for AITAS.

Uses LangChain + ChromaDB + HuggingFace sentence-transformers to build a
per-class vector index over all courseware files.

Moved from root-level rag.py into the backend package.
"""
from __future__ import annotations

import os
import re
import threading
from pathlib import Path
from typing import Callable

from backend.config import CHROMA_DIR

# ---------------------------------------------------------------------------
# Lazy-loaded heavy dependencies (imported once on first use)
# ---------------------------------------------------------------------------
_embeddings_instance = None
_embeddings_lock = threading.Lock()

_chroma_client = None
_chroma_lock = threading.Lock()


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

    except Exception as exc:
        _set_status(class_id, building=False, error=str(exc))
