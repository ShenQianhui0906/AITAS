from __future__ import annotations

import tempfile
import unittest
import sqlite3
from pathlib import Path
from unittest.mock import patch

import backend.database as database
from backend.app import create_app
from backend.services import sync_service


class MessageRouteTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = database.DB_PATH
        database.DB_PATH = Path(self.temp_dir.name) / "messages.sqlite3"

        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()
        self.teacher = self._login("teacher01", "Teacher@123")
        self.student = self._login("student01", "Student@123")

        conn = database.get_conn()
        cursor = conn.execute(
            "INSERT INTO classes (name, description, teacher_id, created_at) "
            "VALUES ('私信测试班', '', ?, '2026-01-01 09:00:00')",
            (self.teacher["user"]["id"],),
        )
        class_id = cursor.lastrowid
        conn.executemany(
            "INSERT INTO class_members (class_id, user_id, joined_at) VALUES (?, ?, ?)",
            [
                (class_id, self.teacher["user"]["id"], "2026-01-01 09:00:00"),
                (class_id, self.student["user"]["id"], "2026-01-01 09:00:00"),
            ],
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        database.DB_PATH = self.original_db_path
        self.temp_dir.cleanup()

    def _login(self, username: str, password: str) -> dict:
        response = self.client.post(
            "/api/auth/login", json={"username": username, "password": password}
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        payload["headers"] = {"Authorization": f"Bearer {payload['token']}"}
        return payload

    def test_send_returns_renderable_message_and_creates_notification(self):
        response = self.client.post(
            "/api/messages",
            json={
                "receiver_id": self.teacher["user"]["id"],
                "body": "  请问今晚的课件更新了吗？  ",
            },
            headers=self.student["headers"],
        )
        self.assertEqual(response.status_code, 201)
        payload = response.get_json()
        sent = payload["sent_message"]
        self.assertEqual(sent["body"], "请问今晚的课件更新了吗？")
        self.assertEqual(sent["sender_id"], self.student["user"]["id"])
        self.assertEqual(sent["receiver_id"], self.teacher["user"]["id"])
        self.assertEqual(payload["thread_id"], sent["thread_id"])

        thread = self.client.get(
            f"/api/messages/thread/{payload['thread_id']}",
            headers=self.student["headers"],
        )
        self.assertEqual(thread.status_code, 200)
        self.assertEqual(thread.get_json()["messages"][-1]["body"], sent["body"])

        conn = database.get_conn()
        notification = conn.execute(
            "SELECT type, ref_type, ref_id, body FROM notifications "
            "WHERE recipient_id = ? ORDER BY id DESC LIMIT 1",
            (self.teacher["user"]["id"],),
        ).fetchone()
        conn.close()
        self.assertIsNotNone(notification)
        self.assertEqual(notification["type"], "new_message")
        self.assertEqual(notification["ref_type"], "message")
        self.assertEqual(notification["ref_id"], sent["thread_id"])
        self.assertIn(sent["body"], notification["body"])

    def test_deleted_conversation_becomes_visible_after_reopening(self):
        created = self.client.post(
            "/api/messages/conversations",
            json={"user_id": self.teacher["user"]["id"]},
            headers=self.student["headers"],
        )
        self.assertEqual(created.status_code, 200)
        conversations = self.client.get(
            "/api/messages/conversations", headers=self.student["headers"]
        ).get_json()["conversations"]
        self.assertTrue(conversations)
        thread_id = conversations[0]["id"]

        deleted = self.client.delete(
            f"/api/messages/conversations/{thread_id}", headers=self.student["headers"]
        )
        self.assertEqual(deleted.status_code, 200)
        hidden_thread = self.client.get(
            f"/api/messages/thread/{thread_id}", headers=self.student["headers"]
        )
        self.assertEqual(hidden_thread.status_code, 404)

        reopened = self.client.post(
            "/api/messages/conversations",
            json={"user_id": self.teacher["user"]["id"]},
            headers=self.student["headers"],
        )
        self.assertEqual(reopened.status_code, 200)
        self.assertEqual(reopened.get_json()["thread_id"], thread_id)
        visible_thread = self.client.get(
            f"/api/messages/thread/{thread_id}", headers=self.student["headers"]
        )
        self.assertEqual(visible_thread.status_code, 200)

    @patch("backend.routers.messages.wait_for_user_update", return_value=17)
    def test_events_use_client_cursor_and_report_change(self, wait_for_update):
        with patch("backend.routers.messages.get_user_sync_cursor", return_value=15):
            response = self.client.get(
                "/api/messages/events?cursor=12", headers=self.student["headers"]
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["cursor"], 17)
        self.assertTrue(response.get_json()["changed"])
        wait_for_update.assert_called_once_with(
            self.student["user"]["id"], 12, timeout=25.0
        )

    def test_self_messaging_is_rejected(self):
        response = self.client.post(
            "/api/messages",
            json={"receiver_id": self.student["user"]["id"], "body": "hello"},
            headers=self.student["headers"],
        )
        self.assertEqual(response.status_code, 400)


class MessageMigrationTestCase(unittest.TestCase):
    def test_legacy_notification_type_check_is_removed_without_data_loss(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript("""
            CREATE TABLE users (id INTEGER PRIMARY KEY);
            INSERT INTO users (id) VALUES (1);
            CREATE TABLE notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipient_id INTEGER NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('announcement')),
                title TEXT NOT NULL,
                body TEXT NOT NULL DEFAULT '',
                ref_type TEXT,
                ref_id INTEGER,
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            INSERT INTO notifications
                (recipient_id, type, title, body, created_at)
            VALUES (1, 'announcement', '旧通知', '保留我', '2026-01-01 09:00:00');
        """)

        database.ensure_notifications_table_supports_all_types(conn)
        conn.execute(
            "INSERT INTO notifications "
            "(recipient_id, type, title, body, created_at) VALUES (?, ?, ?, ?, ?)",
            (1, "new_message", "新消息", "可写入", "2026-01-01 10:00:00"),
        )
        rows = conn.execute(
            "SELECT type, title FROM notifications ORDER BY id"
        ).fetchall()
        conn.close()

        self.assertEqual(
            [(row["type"], row["title"]) for row in rows],
            [("announcement", "旧通知"), ("new_message", "新消息")],
        )


class MessageSyncServiceTestCase(unittest.TestCase):
    def test_wait_timeout_and_publish_use_monotonic_cursor(self):
        user_id = 987654
        cursor = sync_service.get_user_sync_cursor(user_id)
        self.assertIsNone(
            sync_service.wait_for_user_update(user_id, cursor, timeout=0.01)
        )

        sync_service.publish_user_updates(user_id)
        self.assertGreater(
            sync_service.wait_for_user_update(user_id, cursor, timeout=0.01), cursor
        )


if __name__ == "__main__":
    unittest.main()
