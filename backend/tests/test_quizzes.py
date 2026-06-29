from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import backend.database as database
from backend.app import create_app
from backend.services.quiz_service import auto_grade_submission


class QuizSubmissionReviewTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = database.DB_PATH
        database.DB_PATH = Path(self.temp_dir.name) / "quizzes.sqlite3"

        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()
        self.teacher = self._login("teacher01", "Teacher@123")
        self.student = self._login("student01", "Student@123")

        conn = database.get_conn()
        cursor = conn.execute(
            "INSERT INTO classes (name, description, teacher_id, created_at) "
            "VALUES ('测验复核班', '', ?, '2026-01-01 09:00:00')",
            (self.teacher["user"]["id"],),
        )
        self.class_id = cursor.lastrowid
        conn.executemany(
            "INSERT INTO class_members (class_id, user_id, joined_at) VALUES (?, ?, ?)",
            [
                (self.class_id, self.teacher["user"]["id"], "2026-01-01 09:00:00"),
                (self.class_id, self.student["user"]["id"], "2026-01-01 09:00:00"),
            ],
        )
        conn.commit()
        conn.close()

        published = self.client.post(
            "/api/quizzes",
            json={
                "class_id": self.class_id,
                "title": "软件设计小测",
                "questions": [
                    {
                        "type": "choice",
                        "question": "哪一项属于面向对象原则？",
                        "options": ["A. 封装", "B. 随机复制"],
                        "answer": "A",
                        "explanation": "封装是面向对象的重要原则。",
                    },
                    {
                        "type": "short",
                        "question": "请简述封装的作用。",
                        "answer": "隐藏实现细节并提供稳定接口",
                        "explanation": "关注信息隐藏与稳定接口。",
                    },
                ],
            },
            headers=self.teacher["headers"],
        )
        self.assertEqual(published.status_code, 200)
        self.quiz_id = published.get_json()["quiz_id"]

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

    def _submit_quiz(self) -> dict:
        response = self.client.post(
            f"/api/quizzes/{self.quiz_id}/submit",
            json={
                "answers": [
                    {"question_index": 0, "answer": "A"},
                    {"question_index": 1, "answer": "完全无关的回答"},
                ]
            },
            headers=self.student["headers"],
        )
        self.assertEqual(response.status_code, 200)
        return response.get_json()

    def test_teacher_lists_submission_details_and_reviews_short_answer(self):
        submitted = self._submit_quiz()
        self.assertEqual(submitted["score"], 1)
        self.assertEqual(submitted["pending_short_count"], 1)

        teacher_quizzes = self.client.get(
            "/api/quizzes", headers=self.teacher["headers"]
        ).get_json()["quizzes"]
        quiz_row = next(item for item in teacher_quizzes if item["id"] == self.quiz_id)
        self.assertEqual(quiz_row["submission_count"], 1)

        details_response = self.client.get(
            f"/api/quizzes/{self.quiz_id}/submissions",
            headers=self.teacher["headers"],
        )
        self.assertEqual(details_response.status_code, 200)
        payload = details_response.get_json()
        self.assertEqual(payload["summary"]["submission_count"], 1)
        self.assertEqual(payload["summary"]["pending_review_count"], 1)
        submission = payload["submissions"][0]
        self.assertEqual(submission["student_name"], "李同学")
        self.assertEqual(submission["details"][1]["review_status"], "pending")

        reviewed = self.client.put(
            f"/api/quizzes/{self.quiz_id}/submissions/{submission['id']}/review",
            json={
                "reviews": [
                    {
                        "question_index": 1,
                        "correct": True,
                        "comment": "虽然措辞不同，但核心含义正确。",
                    }
                ]
            },
            headers=self.teacher["headers"],
        )
        self.assertEqual(reviewed.status_code, 200)
        updated = reviewed.get_json()["submission"]
        self.assertEqual(updated["score"], 2)
        self.assertEqual(updated["percentage"], 100.0)
        self.assertEqual(updated["pending_short_count"], 0)
        self.assertEqual(updated["details"][1]["review_status"], "reviewed")
        self.assertEqual(
            updated["details"][1]["manual_review"]["comment"],
            "虽然措辞不同，但核心含义正确。",
        )

        # 批量重新自动批改不应覆盖教师已经保存的人工判定。
        regraded = self.client.post(
            f"/api/quizzes/{self.quiz_id}/grade", headers=self.teacher["headers"]
        )
        self.assertEqual(regraded.status_code, 200)
        student_detail = self.client.get(
            f"/api/quizzes/{self.quiz_id}", headers=self.student["headers"]
        ).get_json()["submission"]
        self.assertEqual(student_detail["score"], 2)
        self.assertEqual(student_detail["pending_short_count"], 0)
        self.assertTrue(student_detail["details"][1]["manual_review"]["correct"])

    def test_review_permissions_and_payload_validation(self):
        submitted = self._submit_quiz()
        submission_id = submitted["submission_id"]

        forbidden = self.client.get(
            f"/api/quizzes/{self.quiz_id}/submissions",
            headers=self.student["headers"],
        )
        self.assertEqual(forbidden.status_code, 403)

        invalid = self.client.put(
            f"/api/quizzes/{self.quiz_id}/submissions/{submission_id}/review",
            json={"reviews": [{"question_index": 0, "correct": True}]},
            headers=self.teacher["headers"],
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertIn("仅简答题", invalid.get_json()["error"])

    def test_student_quiz_payload_hides_answers_before_submission(self):
        response = self.client.get(
            f"/api/quizzes?class_id={self.class_id}", headers=self.student["headers"]
        )
        self.assertEqual(response.status_code, 200)
        questions = response.get_json()["quizzes"][0]["questions"]
        self.assertNotIn("answer", questions[0])
        self.assertNotIn("explanation", questions[0])


class QuizAutomaticGradingTestCase(unittest.TestCase):
    def test_multi_choice_answers_are_compared_as_sets(self):
        result = auto_grade_submission(
            [{"type": "multi_choice", "answer": ["A", "C"]}],
            [{"question_index": 0, "answer": "C,A"}],
        )
        self.assertEqual(result["score"], 1)


if __name__ == "__main__":
    unittest.main()
