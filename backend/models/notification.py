"""通知模型"""

import sqlite3

from backend.database import now_iso


def create_notification(conn: sqlite3.Connection, recipient_id: int, notif_type: str,
                        title: str, body: str, ref_type: str | None = None,
                        ref_id: int | None = None, *, commit: bool = True) -> int:
    """创建通知"""
    cursor = conn.execute(
        """INSERT INTO notifications
           (recipient_id, type, title, body, ref_type, ref_id, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (recipient_id, notif_type, title, body, ref_type, ref_id, now_iso())
    )
    if commit:
        conn.commit()
    return cursor.lastrowid


def list_notifications(conn: sqlite3.Connection, recipient_id: int,
                       limit: int = 50, offset: int = 0) -> list[dict]:
    """获取用户通知列表"""
    rows = conn.execute(
        """SELECT id, recipient_id, type, title, body, ref_type, ref_id,
                  is_read, created_at
           FROM notifications
           WHERE recipient_id = ?
           ORDER BY created_at DESC
           LIMIT ? OFFSET ?""",
        (recipient_id, limit, offset)
    ).fetchall()
    return [dict(r) for r in rows]


def unread_count(conn: sqlite3.Connection, recipient_id: int) -> int:
    """获取未读通知数量"""
    row = conn.execute(
        "SELECT COUNT(*) FROM notifications WHERE recipient_id = ? AND is_read = 0",
        (recipient_id,)
    ).fetchone()
    return row[0] if row else 0


def mark_read(conn: sqlite3.Connection, notif_id: int, recipient_id: int) -> None:
    """标记单条通知为已读"""
    conn.execute(
        "UPDATE notifications SET is_read = 1 WHERE id = ? AND recipient_id = ?",
        (notif_id, recipient_id)
    )
    conn.commit()


def mark_all_read(conn: sqlite3.Connection, recipient_id: int) -> None:
    """标记所有通知为已读"""
    conn.execute(
        "UPDATE notifications SET is_read = 1 WHERE recipient_id = ?",
        (recipient_id,)
    )
    conn.commit()
