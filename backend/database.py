"""
Database connection, schema initialisation, and seeding.
"""
from __future__ import annotations

import hashlib
import secrets
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path

from backend.config import (
    DB_PATH,
    DB_DIR,
    UPLOAD_DIR,
    TMP_DIR,
    ADMIN_USERNAME,
    ADMIN_PASSWORD,
    ADMIN_DISPLAY_NAME,
    ensure_storage_dirs,
)


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------
def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 10000")
    return conn


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------
def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    ).hex()
    return salt, digest


def verify_password(password: str, salt: str, password_hash: str) -> bool:
    _, digest = hash_password(password, salt)
    return secrets.compare_digest(digest, password_hash)


# ---------------------------------------------------------------------------
# Migration helpers
# ---------------------------------------------------------------------------
def ensure_column(conn: sqlite3.Connection, table_name: str, column_name: str, definition: str):
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}
    if column_name not in columns:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def recreate_users_table_with_admin_role(conn: sqlite3.Connection):
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    student_number_select = "student_number" if "student_number" in columns else "NULL AS student_number"
    conn.commit()
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("""
        CREATE TABLE users_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('teacher', 'student', 'admin')),
            student_number TEXT,
            salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute(f"""
        INSERT INTO users_new (id, username, display_name, role, student_number, salt, password_hash, created_at)
        SELECT id, username, display_name, role, {student_number_select}, salt, password_hash, created_at
        FROM users
    """)
    conn.execute("DROP TABLE users")
    conn.execute("ALTER TABLE users_new RENAME TO users")
    conn.commit()
    conn.execute("PRAGMA foreign_keys = ON")


def ensure_users_table_supports_admin(conn: sqlite3.Connection):
    schema_row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'users'"
    ).fetchone()
    schema_sql = (schema_row["sql"] or "") if schema_row else ""
    if "'admin'" not in schema_sql:
        recreate_users_table_with_admin_role(conn)


# ---------------------------------------------------------------------------
# Row to dict helpers
# ---------------------------------------------------------------------------
def row_to_user(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"],
        "role": row["role"],
        "student_number": row["student_number"],
        "created_at": row["created_at"],
    }


def row_to_class(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "teacher_id": row["teacher_id"],
        "created_at": row["created_at"],
    }


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------
def init_db():
    ensure_storage_dirs()

    conn = get_conn()
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('teacher', 'student', 'admin')),
            student_number TEXT,
            salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            teacher_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(teacher_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS class_members (
            class_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            joined_at TEXT NOT NULL,
            PRIMARY KEY (class_id, user_id),
            FOREIGN KEY(class_id) REFERENCES classes(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS class_join_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('pending', 'approved', 'rejected')),
            requested_at TEXT NOT NULL,
            reviewed_at TEXT,
            reviewed_by INTEGER,
            UNIQUE(class_id, student_id),
            FOREIGN KEY(class_id) REFERENCES classes(id),
            FOREIGN KEY(student_id) REFERENCES users(id),
            FOREIGN KEY(reviewed_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS coursewares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            course_name TEXT NOT NULL,
            description TEXT,
            original_file_name TEXT NOT NULL,
            stored_file_name TEXT NOT NULL,
            uploaded_by INTEGER NOT NULL,
            uploaded_at TEXT NOT NULL,
            class_id INTEGER,
            FOREIGN KEY(uploaded_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            courseware_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            helpfulness INTEGER NOT NULL,
            usability INTEGER NOT NULL,
            suitability INTEGER NOT NULL DEFAULT 3,
            practicality INTEGER NOT NULL DEFAULT 3,
            suggestion TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(courseware_id, student_id),
            FOREIGN KEY(courseware_id) REFERENCES coursewares(id),
            FOREIGN KEY(student_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS discussions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            author_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            class_id INTEGER,
            FOREIGN KEY(author_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS discussion_replies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discussion_id INTEGER NOT NULL,
            body TEXT NOT NULL,
            author_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(discussion_id) REFERENCES discussions(id),
            FOREIGN KEY(author_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS conversation_threads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_one_id INTEGER NOT NULL,
            user_two_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            last_message_at TEXT NOT NULL,
            UNIQUE(user_one_id, user_two_id),
            FOREIGN KEY(user_one_id) REFERENCES users(id),
            FOREIGN KEY(user_two_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS conversation_members (
            thread_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            visible INTEGER NOT NULL DEFAULT 1,
            joined_at TEXT NOT NULL,
            PRIMARY KEY (thread_id, user_id),
            FOREIGN KEY(thread_id) REFERENCES conversation_threads(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            body TEXT NOT NULL,
            is_read INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            thread_id INTEGER
        );

        CREATE TABLE IF NOT EXISTS ai_chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            courseware_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(courseware_id) REFERENCES coursewares(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS rag_chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            sources TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            FOREIGN KEY(class_id) REFERENCES classes(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
    """)

    # Migrations
    ensure_users_table_supports_admin(conn)
    ensure_column(conn, "users", "student_number", "TEXT")
    ensure_column(conn, "coursewares", "class_id", "INTEGER")
    ensure_column(conn, "discussions", "class_id", "INTEGER")
    ensure_column(conn, "messages", "thread_id", "INTEGER")
    ensure_column(conn, "evaluations", "suitability", "INTEGER")
    ensure_column(conn, "evaluations", "practicality", "INTEGER")

    # Indices
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_student_number
        ON users(student_number) WHERE student_number IS NOT NULL AND student_number != ''
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_ai_chat_messages_courseware_user
        ON ai_chat_messages(courseware_id, user_id, id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_rag_chat_messages_class_user
        ON rag_chat_messages(class_id, user_id, id)
    """)

    # Seed data
    seed_demo_users(conn)
    ensure_admin_user(conn)
    seed_classes(conn)
    backfill_class_links(conn)
    seed_courseware(conn)
    seed_discussion(conn)
    seed_messages(conn)
    migrate_message_threads(conn)

    conn.close()


# ---------------------------------------------------------------------------
# Seeding functions
# ---------------------------------------------------------------------------
def seed_demo_users(conn: sqlite3.Connection):
    existing = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
    if existing:
        return
    demo_users = [
        ("teacher01", "王老师", "teacher", None, "Teacher@123"),
        ("student01", "李同学", "student", "20260001", "Student@123"),
        ("student02", "陈同学", "student", "20260002", "Student@123"),
    ]
    for username, display_name, role, student_number, password in demo_users:
        salt, password_hash = hash_password(password)
        conn.execute(
            "INSERT INTO users (username, display_name, role, student_number, salt, password_hash, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (username, display_name, role, student_number, salt, password_hash, now_iso()),
        )
    conn.commit()


def ensure_admin_user(conn: sqlite3.Connection):
    salt, password_hash = hash_password(ADMIN_PASSWORD)
    existing_admin = conn.execute(
        "SELECT id FROM users WHERE role = 'admin' ORDER BY id ASC LIMIT 1"
    ).fetchone()
    if existing_admin:
        conn.execute(
            "UPDATE users SET username = ?, display_name = ?, student_number = NULL, salt = ?, password_hash = ? WHERE id = ?",
            (ADMIN_USERNAME, ADMIN_DISPLAY_NAME, salt, password_hash, existing_admin["id"]),
        )
        conn.execute(
            "DELETE FROM sessions WHERE user_id != ? AND user_id IN (SELECT id FROM users WHERE role = 'admin')",
            (existing_admin["id"],),
        )
        conn.execute(
            "DELETE FROM users WHERE role = 'admin' AND id != ?",
            (existing_admin["id"],),
        )
        conn.commit()
        return
    conn.execute(
        "INSERT INTO users (username, display_name, role, student_number, salt, password_hash, created_at) "
        "VALUES (?, ?, 'admin', NULL, ?, ?, ?)",
        (ADMIN_USERNAME, ADMIN_DISPLAY_NAME, salt, password_hash, now_iso()),
    )
    conn.commit()


def seed_classes(conn: sqlite3.Connection):
    class_rows = conn.execute("SELECT id, teacher_id FROM classes").fetchall()
    for row in class_rows:
        conn.execute(
            "INSERT OR IGNORE INTO class_members (class_id, user_id, joined_at) VALUES (?, ?, ?)",
            (row["id"], row["teacher_id"], now_iso()),
        )
    conn.commit()


def backfill_class_links(conn: sqlite3.Connection):
    default_class = conn.execute("SELECT id FROM classes ORDER BY id LIMIT 1").fetchone()
    if not default_class:
        return
    default_class_id = default_class["id"]
    conn.execute("UPDATE coursewares SET class_id = ? WHERE class_id IS NULL", (default_class_id,))
    conn.execute("UPDATE discussions SET class_id = ? WHERE class_id IS NULL", (default_class_id,))
    conn.commit()


def seed_courseware(conn: sqlite3.Connection):
    existing = conn.execute("SELECT COUNT(*) AS count FROM coursewares").fetchone()["count"]
    if existing:
        return
    teacher = conn.execute("SELECT id FROM users WHERE role = 'teacher' ORDER BY id LIMIT 1").fetchone()
    if not teacher:
        return
    class_row = conn.execute(
        "SELECT id FROM classes WHERE teacher_id = ? ORDER BY id LIMIT 1", (teacher["id"],)
    ).fetchone()
    if not class_row:
        return
    class_id = class_row["id"]

    demo_ext = ".txt"
    demo_content = (
        "AI助教系统演示课件\n\n"
        "1. 系统支持教师上传课件并统一管理。\n"
        "2. 学生可以围绕课件内容进行学习和讨论。\n"
        "3. AI问答界面当前为前端演示版，便于后续接入真实模型。\n"
    )

    temp_name = f"{secrets.token_hex(10)}{demo_ext}"
    temp_path = TMP_DIR / temp_name
    temp_path.write_text(demo_content, encoding="utf-8")

    cursor = conn.execute(
        "INSERT INTO coursewares (title, course_name, description, original_file_name, "
        "stored_file_name, uploaded_by, uploaded_at, class_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "AI助教系统导论", "软件工程课程设计",
            "用于演示课件上传、浏览和前端问答入口的示例课件。",
            "demo_courseware.txt", temp_name, teacher["id"], now_iso(), class_id,
        ),
    )
    courseware_id = cursor.lastrowid

    final_dir = UPLOAD_DIR / "coursewares" / str(courseware_id) / "original"
    final_dir.mkdir(parents=True, exist_ok=True)
    final_name = f"source{demo_ext}"
    final_path = final_dir / final_name
    shutil.move(str(temp_path), str(final_path))
    final_stored = f"coursewares/{courseware_id}/original/{final_name}"

    conn.execute("UPDATE coursewares SET stored_file_name = ? WHERE id = ?", (final_stored, courseware_id))
    conn.commit()


def seed_discussion(conn: sqlite3.Connection):
    existing = conn.execute("SELECT COUNT(*) AS count FROM discussions").fetchone()["count"]
    if existing:
        return
    teacher = conn.execute("SELECT id FROM users WHERE role = 'teacher' ORDER BY id LIMIT 1").fetchone()
    student = conn.execute("SELECT id FROM users WHERE role = 'student' ORDER BY id LIMIT 1").fetchone()
    if not teacher or not student:
        return
    class_row = conn.execute(
        "SELECT id FROM classes WHERE teacher_id = ? ORDER BY id LIMIT 1", (teacher["id"],)
    ).fetchone()
    if not class_row:
        return
    class_id = class_row["id"]
    is_member = conn.execute(
        "SELECT 1 FROM class_members WHERE class_id = ? AND user_id = ?", (class_id, student["id"])
    ).fetchone()
    if not is_member:
        return

    cursor = conn.execute(
        "INSERT INTO discussions (title, body, author_id, created_at, class_id) VALUES (?, ?, ?, ?, ?)",
        ("第一次使用 AI 助教系统时应该先看什么？",
         "建议大家先阅读示例课件，再体验 AI 问答、问卷和讨论区，这样能更快理解系统闭环。",
         student["id"], now_iso(), class_id),
    )
    discussion_id = cursor.lastrowid
    conn.execute(
        "INSERT INTO discussion_replies (discussion_id, body, author_id, created_at) VALUES (?, ?, ?, ?)",
        (discussion_id,
         "可以先从课件详情页进入，里面已经预留了 AI 问答入口，后续也方便扩展真实模型能力。",
         teacher["id"], now_iso()),
    )
    conn.commit()


def seed_messages(conn: sqlite3.Connection):
    existing = conn.execute("SELECT COUNT(*) AS count FROM messages").fetchone()["count"]
    if existing:
        return
    teacher = conn.execute("SELECT id FROM users WHERE role = 'teacher' ORDER BY id LIMIT 1").fetchone()
    student = conn.execute("SELECT id FROM users WHERE role = 'student' ORDER BY id LIMIT 1").fetchone()
    if not teacher or not student:
        return

    # Check if they share a class
    share = conn.execute(
        "SELECT 1 FROM class_members cm1 JOIN class_members cm2 ON cm2.class_id = cm1.class_id "
        "WHERE cm1.user_id = ? AND cm2.user_id = ? LIMIT 1",
        (teacher["id"], student["id"]),
    ).fetchone()
    if not share:
        return

    conn.executemany(
        "INSERT INTO messages (sender_id, receiver_id, body, is_read, created_at) VALUES (?, ?, ?, ?, ?)",
        [
            (student["id"], teacher["id"], "王老师您好，请问课件中的 AI 问答什么时候可以正式使用？", 0, now_iso()),
            (teacher["id"], student["id"], "同学你好，目前已经可以测试使用了，后面会持续完善。", 1, now_iso()),
        ],
    )
    conn.commit()


def normalize_user_pair(user_a, user_b):
    return (user_a, user_b) if user_a < user_b else (user_b, user_a)


def get_or_create_thread(conn: sqlite3.Connection, user_a, user_b, visible_for_a=1, visible_for_b=1):
    user_one, user_two = normalize_user_pair(user_a, user_b)
    row = conn.execute(
        "SELECT id FROM conversation_threads WHERE user_one_id = ? AND user_two_id = ?",
        (user_one, user_two),
    ).fetchone()
    if not row:
        cursor = conn.execute(
            "INSERT INTO conversation_threads (user_one_id, user_two_id, created_at, last_message_at) "
            "VALUES (?, ?, ?, ?)",
            (user_one, user_two, now_iso(), now_iso()),
        )
        thread_id = cursor.lastrowid
    else:
        thread_id = row["id"]

    conn.execute(
        "INSERT OR IGNORE INTO conversation_members (thread_id, user_id, visible, joined_at) VALUES (?, ?, ?, ?)",
        (thread_id, user_a, visible_for_a, now_iso()),
    )
    conn.execute(
        "INSERT OR IGNORE INTO conversation_members (thread_id, user_id, visible, joined_at) VALUES (?, ?, ?, ?)",
        (thread_id, user_b, visible_for_b, now_iso()),
    )
    return thread_id


def migrate_message_threads(conn: sqlite3.Connection):
    rows = conn.execute(
        "SELECT id, sender_id, receiver_id, created_at FROM messages "
        "WHERE thread_id IS NULL ORDER BY id ASC"
    ).fetchall()
    for row in rows:
        thread_id = get_or_create_thread(conn, row["sender_id"], row["receiver_id"])
        conn.execute("UPDATE messages SET thread_id = ? WHERE id = ?", (thread_id, row["id"]))
        conn.execute(
            "UPDATE conversation_threads SET last_message_at = ? WHERE id = ?",
            (row["created_at"], thread_id),
        )
    conn.commit()
