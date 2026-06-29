from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path

import backend.database as database
import backend.models.courseware as courseware_model
import backend.routers.coursewares as courseware_routes
from backend.app import create_app


class NotificationRouteTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = database.DB_PATH
        self.original_courseware_tmp = courseware_model.TMP_DIR
        self.original_courseware_upload = courseware_routes.UPLOAD_DIR

        root = Path(self.temp_dir.name)
        database.DB_PATH = root / "notifications.sqlite3"
        courseware_model.TMP_DIR = root / "tmp"
        courseware_routes.UPLOAD_DIR = root / "uploads"
        courseware_model.TMP_DIR.mkdir(parents=True, exist_ok=True)
        courseware_routes.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()
        self.teacher = self._login("teacher01", "Teacher@123")
        self.student = self._login("student01", "Student@123")
        self.other_student = self._login("student02", "Student@123")

        conn = database.get_conn()
        cursor = conn.execute(
            "INSERT INTO classes (name, description, teacher_id, created_at) "
            "VALUES ('通知测试班', '', ?, '2026-01-01 09:00:00')",
            (self.teacher["user"]["id"],),
        )
        self.class_id = cursor.lastrowid
        conn.executemany(
            "INSERT INTO class_members (class_id, user_id, joined_at) VALUES (?, ?, ?)",
            [
                (self.class_id, self.teacher["user"]["id"], "2026-01-01 09:00:00"),
                (self.class_id, self.student["user"]["id"], "2026-01-01 09:00:00"),
                (self.class_id, self.other_student["user"]["id"], "2026-01-01 09:00:00"),
            ],
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        database.DB_PATH = self.original_db_path
        courseware_model.TMP_DIR = self.original_courseware_tmp
        courseware_routes.UPLOAD_DIR = self.original_courseware_upload
        self.temp_dir.cleanup()

    def _login(self, username: str, password: str) -> dict:
        response = self.client.post(
            "/api/auth/login", json={"username": username, "password": password}
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        payload["headers"] = {"Authorization": f"Bearer {payload['token']}"}
        return payload

    def _notifications(self, user: dict) -> list[dict]:
        response = self.client.get("/api/notifications", headers=user["headers"])
        self.assertEqual(response.status_code, 200)
        return response.get_json()["notifications"]

    def _upload_courseware(self) -> dict:
        response = self.client.post(
            "/api/coursewares",
            data={
                "class_id": str(self.class_id),
                "title": "需求分析课件",
                "course_name": "软件工程",
                "description": "通知测试",
                "file": (io.BytesIO(b"requirements notes"), "requirements.txt"),
            },
            headers=self.teacher["headers"],
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 201)
        return response.get_json()["courseware"]

    def test_students_receive_assignment_quiz_and_courseware_notifications(self):
        assignment = self.client.post(
            "/api/assignments",
            json={
                "class_id": self.class_id,
                "title": "需求规格说明书",
                "description": "完成 SRS",
                "due_at": "2027-06-30T23:59",
            },
            headers=self.teacher["headers"],
        )
        self.assertEqual(assignment.status_code, 201)

        quiz = self.client.post(
            "/api/quizzes",
            json={
                "class_id": self.class_id,
                "title": "需求分析小测",
                "questions": [
                    {
                        "type": "choice",
                        "question": "SRS 是什么？",
                        "options": ["A", "B"],
                        "answer": "A",
                    }
                ],
            },
            headers=self.teacher["headers"],
        )
        self.assertEqual(quiz.status_code, 200)
        courseware = self._upload_courseware()

        for student in (self.student, self.other_student):
            notifications = self._notifications(student)
            by_type = {notification["type"]: notification for notification in notifications}
            self.assertTrue({
                "assignment_published",
                "quiz_published",
                "courseware_uploaded",
            }.issubset(by_type))
            self.assertEqual(
                by_type["assignment_published"]["ref_id"],
                assignment.get_json()["assignment"]["id"],
            )
            self.assertEqual(by_type["quiz_published"]["ref_id"], quiz.get_json()["quiz_id"])
            self.assertEqual(by_type["courseware_uploaded"]["ref_id"], courseware["id"])

    def test_teacher_receives_feedback_and_private_message_notifications(self):
        courseware = self._upload_courseware()
        feedback = self.client.post(
            "/api/evaluations",
            json={
                "courseware_id": courseware["id"],
                "helpfulness": 5,
                "usability": 4,
                "suitability": 5,
                "practicality": 4,
                "suggestion": "希望增加更多案例",
            },
            headers=self.student["headers"],
        )
        self.assertEqual(feedback.status_code, 201)

        message = self.client.post(
            "/api/messages",
            json={
                "receiver_id": self.teacher["user"]["id"],
                "body": "老师您好，请查收我的反馈。",
            },
            headers=self.student["headers"],
        )
        self.assertEqual(message.status_code, 201)

        notifications = self._notifications(self.teacher)
        by_type = {notification["type"]: notification for notification in notifications}
        self.assertIn("feedback_received", by_type)
        self.assertIn("new_message", by_type)
        self.assertIn("希望增加更多案例", by_type["feedback_received"]["body"])
        self.assertEqual(
            by_type["new_message"]["ref_id"], message.get_json()["thread_id"]
        )

        unread = self.client.get(
            "/api/notifications/unread-count", headers=self.teacher["headers"]
        )
        self.assertEqual(unread.status_code, 200)
        self.assertEqual(unread.get_json()["count"], 2)

    def test_private_message_also_notifies_student_recipient(self):
        message = self.client.post(
            "/api/messages",
            json={
                "receiver_id": self.student["user"]["id"],
                "body": "请记得查看新课件。",
            },
            headers=self.teacher["headers"],
        )
        self.assertEqual(message.status_code, 201)
        notifications = self._notifications(self.student)
        private_messages = [
            notification for notification in notifications
            if notification["type"] == "new_message"
        ]
        self.assertEqual(len(private_messages), 1)
        self.assertEqual(private_messages[0]["ref_id"], message.get_json()["thread_id"])


if __name__ == "__main__":
    unittest.main()
