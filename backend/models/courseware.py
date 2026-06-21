"""
Courseware model — CRUD for coursewares table.
"""
from __future__ import annotations

import secrets
import sqlite3
import shutil
from pathlib import Path

from backend.database import now_iso
from backend.config import UPLOAD_DIR, TMP_DIR, QUICKLOOK_PREVIEW_SUFFIXES


def list_coursewares(
    conn: sqlite3.Connection,
    class_clause: str,
    class_params: list,
    build_viewer_url_fn,
) -> list[dict]:
    rows = conn.execute(f"""
        SELECT c.id, c.title, c.course_name, c.description, c.original_file_name,
               c.stored_file_name, c.uploaded_at, c.class_id,
               cls.name AS class_name, u.display_name AS teacher_name, u.id AS teacher_id
        FROM coursewares c
        JOIN classes cls ON cls.id = c.class_id
        JOIN users u ON u.id = c.uploaded_by
        WHERE {class_clause}
        ORDER BY c.uploaded_at DESC
    """, class_params).fetchall()

    coursewares = []
    for row in rows:
        item = dict(row)
        item["viewer_url"] = build_viewer_url_fn(row["stored_file_name"], row["title"])
        coursewares.append(item)
    return coursewares


def get_courseware_detail(conn: sqlite3.Connection, courseware_id: int, build_viewer_url_fn) -> dict | None:
    row = conn.execute("""
        SELECT c.id, c.title, c.course_name, c.description, c.original_file_name,
               c.stored_file_name, c.uploaded_at, c.class_id,
               cls.name AS class_name, u.display_name AS teacher_name
        FROM coursewares c
        JOIN classes cls ON cls.id = c.class_id
        JOIN users u ON u.id = c.uploaded_by
        WHERE c.id = ?
    """, (courseware_id,)).fetchone()

    if not row:
        return None
    item = dict(row)
    item["viewer_url"] = build_viewer_url_fn(row["stored_file_name"], row["title"])
    return item


def create_courseware(
    conn: sqlite3.Connection,
    title: str,
    course_name: str,
    description: str,
    original_name: str,
    file_data: bytes,
    uploaded_by: int,
    class_id: int,
    ensure_native_pdf_preview_fn=None,
    ensure_quicklook_preview_fn=None,
) -> dict:
    ext = Path(original_name).suffix

    # Phase 1: save to temp, insert DB
    temp_name = f"{secrets.token_hex(10)}{ext}"
    temp_path = TMP_DIR / temp_name
    temp_path.write_bytes(file_data)

    cursor = conn.execute(
        "INSERT INTO coursewares (title, course_name, description, original_file_name, "
        "stored_file_name, uploaded_by, uploaded_at, class_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (title, course_name, description, original_name, temp_name, uploaded_by, now_iso(), class_id),
    )
    courseware_id = cursor.lastrowid

    # Phase 2: move to final location
    final_dir = UPLOAD_DIR / "coursewares" / str(courseware_id) / "original"
    final_dir.mkdir(parents=True, exist_ok=True)
    final_name = f"source{ext}"
    final_path = final_dir / final_name
    shutil.move(str(temp_path), str(final_path))
    stored_file_name = f"coursewares/{courseware_id}/original/{final_name}"

    conn.execute(
        "UPDATE coursewares SET stored_file_name = ? WHERE id = ?",
        (stored_file_name, courseware_id),
    )

    # Generate previews for presentations
    if final_path.suffix.lower() in QUICKLOOK_PREVIEW_SUFFIXES:
        if ensure_native_pdf_preview_fn:
            result = ensure_native_pdf_preview_fn(final_path)
            if result is None and ensure_quicklook_preview_fn:
                ensure_quicklook_preview_fn(final_path)
        elif ensure_quicklook_preview_fn:
            ensure_quicklook_preview_fn(final_path)

    conn.commit()
    return _get_courseware_with_joins(conn, courseware_id)


def update_courseware(
    conn: sqlite3.Connection,
    courseware_id: int,
    title: str,
    course_name: str,
    description: str,
) -> dict | None:
    conn.execute(
        "UPDATE coursewares SET title=?, course_name=?, description=? WHERE id=?",
        (title, course_name, description, courseware_id),
    )
    conn.commit()
    return _get_courseware_with_joins(conn, courseware_id)


def delete_courseware(conn: sqlite3.Connection, courseware_id: int) -> dict | None:
    row = conn.execute(
        "SELECT stored_file_name, class_id FROM coursewares WHERE id = ?", (courseware_id,)
    ).fetchone()
    if not row:
        return None
    stored_file_name = row["stored_file_name"]

    conn.execute("DELETE FROM ai_chat_messages WHERE courseware_id = ?", (courseware_id,))
    conn.execute("DELETE FROM evaluations WHERE courseware_id = ?", (courseware_id,))
    conn.execute("DELETE FROM coursewares WHERE id = ?", (courseware_id,))
    conn.commit()

    return {"stored_file_name": stored_file_name, "class_id": row["class_id"]}


def _get_courseware_with_joins(conn: sqlite3.Connection, courseware_id: int) -> dict | None:
    row = conn.execute("""
        SELECT c.id, c.title, c.course_name, c.description, c.original_file_name,
               c.stored_file_name, c.uploaded_at, c.class_id,
               cls.name AS class_name, u.display_name AS teacher_name, u.id AS teacher_id
        FROM coursewares c
        JOIN classes cls ON cls.id = c.class_id
        JOIN users u ON u.id = c.uploaded_by
        WHERE c.id = ?
    """, (courseware_id,)).fetchone()
    return dict(row) if row else None
