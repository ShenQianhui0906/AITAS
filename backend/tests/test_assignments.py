from __future__ import annotations

import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import backend.database as database
import backend.routers.assignments as assignment_routes
import backend.services.assignment_grading_service as grading_service
import backend.services.assignment_service as assignment_service
from backend.app import create_app


class AssignmentRouteTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = database.DB_PATH
        self.original_service_upload = assignment_service.UPLOAD_DIR
        self.original_route_upload = assignment_routes.UPLOAD_DIR
        self.original_grading_upload = grading_service.UPLOAD_DIR
        database.DB_PATH = Path(self.temp_dir.name) / "assignments.sqlite3"
        test_upload_dir = Path(self.temp_dir.name) / "uploads"
        test_upload_dir.mkdir(parents=True, exist_ok=True)
        assignment_service.UPLOAD_DIR = test_upload_dir
        assignment_routes.UPLOAD_DIR = test_upload_dir
        grading_service.UPLOAD_DIR = test_upload_dir

        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

        self.teacher = self._login("teacher01", "Teacher@123")
        self.student = self._login("student01", "Student@123")
        self.other_student = self._login("student02", "Student@123")

        conn = database.get_conn()
        cursor = conn.execute(
            "INSERT INTO classes (name, description, teacher_id, created_at) "
            "VALUES ('作业测试班', '', ?, '2026-01-01 09:00:00')",
            (self.teacher["user"]["id"],),
        )
        self.class_id = cursor.lastrowid
        conn.execute(
            "INSERT INTO class_members (class_id, user_id, joined_at) VALUES (?, ?, ?)",
            (self.class_id, self.student["user"]["id"], "2026-01-01 09:00:00"),
        )
        conn.execute(
            "INSERT INTO class_members (class_id, user_id, joined_at) VALUES (?, ?, ?)",
            (self.class_id, self.other_student["user"]["id"], "2026-01-01 09:00:00"),
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        database.DB_PATH = self.original_db_path
        assignment_service.UPLOAD_DIR = self.original_service_upload
        assignment_routes.UPLOAD_DIR = self.original_route_upload
        grading_service.UPLOAD_DIR = self.original_grading_upload
        self.temp_dir.cleanup()

    def _login(self, username: str, password: str) -> dict:
        response = self.client.post(
            "/api/auth/login", json={"username": username, "password": password}
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        payload["headers"] = {"Authorization": f"Bearer {payload['token']}"}
        return payload

    def _publish_assignment(self) -> int:
        response = self.client.post(
            "/api/assignments",
            json={
                "class_id": self.class_id,
                "title": "课程设计报告",
                "description": "提交正文、截图和报告文件",
                "due_at": "2027-06-30T23:59",
            },
            headers=self.teacher["headers"],
        )
        self.assertEqual(response.status_code, 201)
        return response.get_json()["assignment"]["id"]

    def _submit_text_assignment(
        self, assignment_id: int, user: dict | None = None, text: str = "提交正文"
    ) -> dict:
        response = self.client.post(
            f"/api/assignments/{assignment_id}/submit",
            data={
                "content_html": f"<p>{text}</p>",
                "attachments": (io.BytesIO(b"attachment evidence"), "evidence.txt"),
            },
            headers=(user or self.student)["headers"],
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        return response.get_json()["submission"]

    def test_assignment_database_tables_and_grade_columns_exist(self):
        conn = database.get_conn()
        table_names = {
            row["name"] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        self.assertTrue({
            "assignments",
            "assignment_submissions",
            "assignment_submission_files",
            "assignment_grading_rubrics",
            "assignment_ai_grading_records",
        }.issubset(table_names))
        submission_columns = {
            row["name"] for row in conn.execute(
                "PRAGMA table_info(assignment_submissions)"
            ).fetchall()
        }
        conn.close()
        self.assertTrue({"score", "feedback", "graded_at", "graded_by"}.issubset(
            submission_columns
        ))

    def test_each_assignment_has_an_independent_rubric(self):
        first_assignment = self._publish_assignment()
        second_assignment = self._publish_assignment()
        first_response = self.client.put(
            f"/api/assignments/{first_assignment}/rubric",
            json={"content": "第一项作业评分标准"},
            headers=self.teacher["headers"],
        )
        self.assertEqual(first_response.status_code, 200)

        second_before_save = self.client.get(
            f"/api/assignments/{second_assignment}/rubric",
            headers=self.teacher["headers"],
        )
        self.assertEqual(second_before_save.status_code, 200)
        self.assertIsNone(second_before_save.get_json()["rubric"])

        second_response = self.client.put(
            f"/api/assignments/{second_assignment}/rubric",
            json={"content": "第二项作业评分标准"},
            headers=self.teacher["headers"],
        )
        self.assertEqual(second_response.status_code, 200)
        conn = database.get_conn()
        rows = conn.execute(
            "SELECT assignment_id, content FROM assignment_grading_rubrics "
            "ORDER BY assignment_id"
        ).fetchall()
        conn.close()
        self.assertEqual(len(rows), 2)
        self.assertNotEqual(rows[0]["content"], rows[1]["content"])

    def test_teacher_dashboard_includes_assignment_and_student_insights(self):
        assignment_id = self._publish_assignment()
        self._submit_text_assignment(assignment_id)
        response = self.client.get(
            f"/api/dashboard?class_id={self.class_id}",
            headers=self.teacher["headers"],
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["stats"]["assignments"], 1)
        progress = payload["insights"]["assignment_progress"]
        self.assertEqual(progress["student_count"], 2)
        self.assertEqual(progress["expected_submissions"], 2)
        self.assertEqual(progress["submitted_count"], 1)
        self.assertEqual(progress["completion_rate"], 50)
        self.assertEqual(len(payload["insights"]["student_progress"]), 2)
        self.assertEqual(len(payload["insights"]["feedback"]["dimensions"]), 4)

    def test_legacy_class_rubric_is_copied_to_existing_assignments(self):
        first_assignment = self._publish_assignment()
        second_assignment = self._publish_assignment()
        conn = database.get_conn()
        conn.execute("DROP TABLE assignment_grading_rubrics")
        conn.execute(
            """
            CREATE TABLE class_grading_rubrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_id INTEGER NOT NULL UNIQUE,
                content TEXT NOT NULL,
                source TEXT NOT NULL,
                source_refs TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT INTO class_grading_rubrics "
            "(class_id, content, source, source_refs, created_at, updated_at) "
            "VALUES (?, '原班级评分标准', 'teacher', '[]', ?, ?)",
            (self.class_id, "2026-01-01 10:00:00", "2026-01-01 10:00:00"),
        )
        conn.commit()
        conn.close()

        database.init_db()
        conn = database.get_conn()
        legacy_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' "
            "AND name = 'class_grading_rubrics'"
        ).fetchone()
        rows = conn.execute(
            "SELECT assignment_id, content FROM assignment_grading_rubrics "
            "WHERE assignment_id IN (?, ?) ORDER BY assignment_id",
            (first_assignment, second_assignment),
        ).fetchall()
        conn.close()
        self.assertIsNone(legacy_exists)
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row["content"] == "原班级评分标准" for row in rows))

    @patch("backend.services.assignment_grading_service.retrieve_class_knowledge")
    @patch("backend.services.assignment_grading_service.call_bigmodel_chat")
    def test_ai_grading_persists_draft_then_confirms_with_formal_grade(
        self, chat, retrieve
    ):
        assignment_id = self._publish_assignment()
        submission = self._submit_text_assignment(
            assignment_id, text="完成了需求分析和系统设计"
        )
        retrieve.return_value = {
            "knowledge_text": "",
            "sources": [],
            "related_coursewares": [],
            "retriever_error": None,
        }
        chat.side_effect = [
            '{"rubric":"需求分析40分；系统设计40分；表达质量20分"}',
            '{"score":86.5,"feedback":{"evaluation":"整体完整",'
            '"evidence":"正文包含需求分析和系统设计，附件提供了补充依据"}}',
        ]

        response = self.client.post(
            f"/api/assignments/{assignment_id}/submissions/{submission['id']}/ai-grade",
            headers=self.teacher["headers"],
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["suggestion"]["score"], 86.5)
        self.assertEqual(payload["rubric"]["source"], "assignment")
        grading_prompt = chat.call_args_list[-1].args[0][-1]["content"]
        self.assertIn("完成了需求分析和系统设计", grading_prompt)
        self.assertIn("attachment evidence", grading_prompt)

        conn = database.get_conn()
        formal = conn.execute(
            "SELECT score, feedback, graded_at FROM assignment_submissions WHERE id = ?",
            (submission["id"],),
        ).fetchone()
        draft = conn.execute(
            "SELECT status, score FROM assignment_ai_grading_records WHERE submission_id = ?",
            (submission["id"],),
        ).fetchone()
        conn.close()
        self.assertIsNone(formal["score"])
        self.assertIsNone(formal["graded_at"])
        self.assertEqual(draft["status"], "draft")

        detail = self.client.get(
            f"/api/assignments/{assignment_id}", headers=self.teacher["headers"]
        ).get_json()["assignment"]
        self.assertEqual(detail["submissions"][0]["ai_draft"]["score"], 86.5)

        save_response = self.client.put(
            f"/api/assignments/{assignment_id}/submissions/{submission['id']}/grade",
            json={"score": 87, "feedback": payload["suggestion"]["feedback"]},
            headers=self.teacher["headers"],
        )
        self.assertEqual(save_response.status_code, 200)
        conn = database.get_conn()
        formal = conn.execute(
            "SELECT score, feedback, graded_at FROM assignment_submissions WHERE id = ?",
            (submission["id"],),
        ).fetchone()
        record_status = conn.execute(
            "SELECT status FROM assignment_ai_grading_records WHERE submission_id = ?",
            (submission["id"],),
        ).fetchone()["status"]
        conn.close()
        self.assertEqual(formal["score"], 87)
        self.assertIsNotNone(formal["graded_at"])
        self.assertEqual(record_status, "confirmed")

    @patch("backend.services.assignment_grading_service.retrieve_class_knowledge")
    @patch("backend.services.assignment_grading_service.call_bigmodel_chat")
    def test_ai_grading_prefers_knowledge_base_rubric(self, chat, retrieve):
        assignment_id = self._publish_assignment()
        submission = self._submit_text_assignment(assignment_id)
        retrieve.return_value = {
            "knowledge_text": "课程要求：功能完整性占60%，测试质量占40%。",
            "sources": [{"courseware_id": 7, "title": "课程要求"}],
            "related_coursewares": [],
            "retriever_error": None,
        }
        chat.side_effect = [
            '{"found":true,"rubric":"功能完整性60分；测试质量40分"}',
            '{"score":75,"feedback":{"evaluation":"基本完成",'
            '"evidence":"提交包含正文和附件，但测试依据有限"}}',
        ]
        response = self.client.post(
            f"/api/assignments/{assignment_id}/submissions/{submission['id']}/ai-grade",
            headers=self.teacher["headers"],
        )
        self.assertEqual(response.status_code, 200)
        rubric = response.get_json()["rubric"]
        self.assertEqual(rubric["source"], "knowledge_base")
        self.assertEqual(rubric["source_refs"][0]["title"], "课程要求")

    @patch("backend.services.assignment_grading_service.retrieve_class_knowledge")
    @patch("backend.services.assignment_grading_service.call_bigmodel_chat")
    def test_ai_grading_uses_history_and_rejects_invalid_json(self, chat, retrieve):
        previous_assignment = self._publish_assignment()
        previous_submission = self._submit_text_assignment(previous_assignment)
        grade_response = self.client.put(
            f"/api/assignments/{previous_assignment}/submissions/{previous_submission['id']}/grade",
            json={"score": 91, "feedback": "功能完整，测试充分"},
            headers=self.teacher["headers"],
        )
        self.assertEqual(grade_response.status_code, 200)

        assignment_id = self._publish_assignment()
        submission = self._submit_text_assignment(
            assignment_id, user=self.other_student, text="新的课程设计提交"
        )
        retrieve.return_value = {
            "knowledge_text": "",
            "sources": [],
            "related_coursewares": [],
            "retriever_error": None,
        }
        chat.side_effect = [
            '{"rubric":"功能完整性50分；测试质量30分；表达20分"}',
            "not-json",
        ]
        response = self.client.post(
            f"/api/assignments/{assignment_id}/submissions/{submission['id']}/ai-grade",
            headers=self.teacher["headers"],
        )
        self.assertEqual(response.status_code, 502)
        history_prompt = chat.call_args_list[0].args[0][-1]["content"]
        self.assertIn("功能完整，测试充分", history_prompt)
        conn = database.get_conn()
        rubric_source = conn.execute(
            "SELECT source FROM assignment_grading_rubrics WHERE assignment_id = ?",
            (assignment_id,),
        ).fetchone()["source"]
        draft_count = conn.execute(
            "SELECT COUNT(*) AS count FROM assignment_ai_grading_records "
            "WHERE submission_id = ?",
            (submission["id"],),
        ).fetchone()["count"]
        official_score = conn.execute(
            "SELECT score FROM assignment_submissions WHERE id = ?",
            (submission["id"],),
        ).fetchone()["score"]
        conn.close()
        self.assertEqual(rubric_source, "history")
        self.assertEqual(draft_count, 0)
        self.assertIsNone(official_score)

    @patch("backend.services.assignment_grading_service.retrieve_class_knowledge")
    @patch("backend.services.assignment_grading_service.call_bigmodel_chat")
    def test_rubric_management_and_ai_draft_discard(self, chat, retrieve):
        assignment_id = self._publish_assignment()
        submission = self._submit_text_assignment(assignment_id)

        save_rubric_response = self.client.put(
            f"/api/assignments/{assignment_id}/rubric",
            json={"content": "内容质量70分；表达规范30分"},
            headers=self.teacher["headers"],
        )
        self.assertEqual(save_rubric_response.status_code, 200)
        self.assertEqual(save_rubric_response.get_json()["rubric"]["source"], "teacher")

        chat.return_value = (
            '{"score":82,"feedback":{"evaluation":"内容较完整",'
            '"evidence":"正文和附件均提供了作答依据"}}'
        )
        ai_response = self.client.post(
            f"/api/assignments/{assignment_id}/submissions/{submission['id']}/ai-grade",
            headers=self.teacher["headers"],
        )
        self.assertEqual(ai_response.status_code, 200)
        self.assertEqual(chat.call_count, 1)

        discard_response = self.client.delete(
            f"/api/assignments/{assignment_id}/submissions/{submission['id']}/ai-grade",
            headers=self.teacher["headers"],
        )
        self.assertEqual(discard_response.status_code, 200)
        detail = self.client.get(
            f"/api/assignments/{assignment_id}", headers=self.teacher["headers"]
        ).get_json()["assignment"]
        self.assertIsNone(detail["submissions"][0]["ai_draft"])

        retrieve.return_value = {
            "knowledge_text": "",
            "sources": [],
            "related_coursewares": [],
            "retriever_error": None,
        }
        chat.reset_mock()
        chat.return_value = '{"rubric":"候选标准：任务完成度60分；质量40分"}'
        regenerate_response = self.client.post(
            f"/api/assignments/{assignment_id}/rubric/regenerate",
            headers=self.teacher["headers"],
        )
        self.assertEqual(regenerate_response.status_code, 200)
        self.assertEqual(
            regenerate_response.get_json()["candidate"]["source"], "assignment"
        )
        persisted = self.client.get(
            f"/api/assignments/{assignment_id}/rubric",
            headers=self.teacher["headers"],
        ).get_json()["rubric"]
        self.assertEqual(persisted["content"], "内容质量70分；表达规范30分")

        forbidden_response = self.client.post(
            f"/api/assignments/{assignment_id}/submissions/{submission['id']}/ai-grade",
            headers=self.student["headers"],
        )
        self.assertEqual(forbidden_response.status_code, 403)

        delete_class_response = self.client.delete(
            f"/api/classes/{self.class_id}", headers=self.teacher["headers"]
        )
        self.assertEqual(delete_class_response.status_code, 200)
        conn = database.get_conn()
        rubric_count = conn.execute(
            "SELECT COUNT(*) AS count FROM assignment_grading_rubrics",
        ).fetchone()["count"]
        ai_record_count = conn.execute(
            "SELECT COUNT(*) AS count FROM assignment_ai_grading_records"
        ).fetchone()["count"]
        conn.close()
        self.assertEqual(rubric_count, 0)
        self.assertEqual(ai_record_count, 0)

    def test_publish_submit_files_grade_and_delete(self):
        assignment_id = self._publish_assignment()

        docx_body = io.BytesIO()
        with zipfile.ZipFile(docx_body, "w") as archive:
            archive.writestr(
                "word/document.xml",
                '<w:document xmlns:w="urn:test"><w:body><w:p>'
                '<w:r><w:t>Word assignment</w:t></w:r>'
                '<w:r><w:t> answer</w:t></w:r>'
                '</w:p></w:body></w:document>',
            )
        docx_body.seek(0)

        list_response = self.client.get(
            f"/api/assignments?class_id={self.class_id}",
            headers=self.student["headers"],
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.get_json()["assignments"][0]["submission_status"], "pending")

        submit_response = self.client.post(
            f"/api/assignments/{assignment_id}/submit",
            data={
                "content_html": (
                    '<p>我的正文<script>alert(1)</script>'
                    '<img data-inline-index="0" onerror="alert(1)"></p>'
                ),
                "inline_images": (io.BytesIO(b"fake-png"), "answer.png"),
                "attachments": [
                    (io.BytesIO(b"report-body"), "report.txt"),
                    (docx_body, "answer.docx"),
                ],
            },
            headers=self.student["headers"],
            content_type="multipart/form-data",
        )
        self.assertEqual(submit_response.status_code, 200)
        submission = submit_response.get_json()["submission"]
        self.assertIn("我的正文", submission["content_html"])
        self.assertIn("data-assignment-file-id", submission["content_html"])
        self.assertNotIn("script", submission["content_html"])
        self.assertNotIn("onerror", submission["content_html"])
        self.assertEqual(len(submission["files"]), 3)

        inline_file = next(file for file in submission["files"] if file["is_inline"])
        attachment_file = next(
            file for file in submission["files"]
            if file["original_file_name"] == "report.txt"
        )
        docx_file = next(
            file for file in submission["files"]
            if file["original_file_name"] == "answer.docx"
        )
        owner_file_response = self.client.get(
            inline_file["url"], headers=self.student["headers"]
        )
        self.assertEqual(owner_file_response.status_code, 200)
        owner_file_response.close()
        other_file_response = self.client.get(
            inline_file["url"], headers=self.other_student["headers"]
        )
        self.assertEqual(other_file_response.status_code, 403)

        preview_response = self.client.get(
            attachment_file["url"], headers=self.student["headers"]
        )
        self.assertEqual(preview_response.status_code, 200)
        self.assertTrue(
            preview_response.headers["Content-Disposition"].startswith("inline")
        )
        preview_response.close()
        document_preview_response = self.client.get(
            f'{attachment_file["url"]}/preview', headers=self.student["headers"]
        )
        self.assertEqual(document_preview_response.status_code, 200)
        self.assertIn("text/html", document_preview_response.content_type)
        self.assertIn(b"report-body", document_preview_response.data)
        document_preview_response.close()
        docx_preview_response = self.client.get(
            f'{docx_file["url"]}/preview', headers=self.student["headers"]
        )
        self.assertEqual(docx_preview_response.status_code, 200)
        self.assertIn("text/html", docx_preview_response.content_type)
        self.assertIn(b"Word assignment answer", docx_preview_response.data)
        self.assertNotIn(b"Word assignment\nanswer", docx_preview_response.data)
        docx_preview_response.close()
        forbidden_preview_response = self.client.get(
            f'{attachment_file["url"]}/preview', headers=self.other_student["headers"]
        )
        self.assertEqual(forbidden_preview_response.status_code, 403)
        download_response = self.client.get(
            f'{attachment_file["url"]}?download=1', headers=self.student["headers"]
        )
        self.assertTrue(
            download_response.headers["Content-Disposition"].startswith("attachment")
        )
        download_response.close()

        other_submit_response = self.client.post(
            f"/api/assignments/{assignment_id}/submit",
            data={"content_html": "<p>第二位学生的答案</p>"},
            headers=self.other_student["headers"],
            content_type="multipart/form-data",
        )
        self.assertEqual(other_submit_response.status_code, 200)
        other_submission = other_submit_response.get_json()["submission"]
        other_grade_response = self.client.put(
            f"/api/assignments/{assignment_id}/submissions/{other_submission['id']}/grade",
            json={"score": 88, "feedback": "已批改"},
            headers=self.teacher["headers"],
        )
        self.assertEqual(other_grade_response.status_code, 200)

        teacher_detail_response = self.client.get(
            f"/api/assignments/{assignment_id}", headers=self.teacher["headers"]
        )
        ordered_submissions = teacher_detail_response.get_json()["assignment"]["submissions"]
        self.assertEqual(ordered_submissions[0]["id"], submission["id"])
        self.assertEqual(ordered_submissions[0]["status"], "submitted")
        self.assertEqual(ordered_submissions[1]["status"], "graded")

        grade_response = self.client.put(
            f"/api/assignments/{assignment_id}/submissions/{submission['id']}/grade",
            json={"score": 92.5, "feedback": "结构清晰，继续完善测试部分。"},
            headers=self.teacher["headers"],
        )
        self.assertEqual(grade_response.status_code, 200)
        self.assertEqual(grade_response.get_json()["submission"]["score"], 92.5)

        detail_response = self.client.get(
            f"/api/assignments/{assignment_id}", headers=self.student["headers"]
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(
            detail_response.get_json()["assignment"]["my_submission"]["status"],
            "graded",
        )

        resubmit_response = self.client.post(
            f"/api/assignments/{assignment_id}/submit",
            data={"content_html": "<p>再次提交</p>"},
            headers=self.student["headers"],
            content_type="multipart/form-data",
        )
        self.assertEqual(resubmit_response.status_code, 400)

        delete_response = self.client.delete(
            f"/api/assignments/{assignment_id}", headers=self.teacher["headers"]
        )
        self.assertEqual(delete_response.status_code, 200)
        conn = database.get_conn()
        count = conn.execute(
            "SELECT COUNT(*) AS count FROM assignments WHERE id = ?", (assignment_id,)
        ).fetchone()["count"]
        conn.close()
        self.assertEqual(count, 0)

    def test_students_cannot_publish_or_grade(self):
        response = self.client.post(
            "/api/assignments",
            json={
                "class_id": self.class_id,
                "title": "越权作业",
                "due_at": "2027-06-30T23:59",
            },
            headers=self.student["headers"],
        )
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
