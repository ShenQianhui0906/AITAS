from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import backend.database as database
from backend.app import create_app
from backend.services.agent_service import classify_agent_intent


class AgentIntentTestCase(unittest.TestCase):
    @patch(
        "backend.services.agent_service.call_bigmodel_chat",
        side_effect=RuntimeError("model unavailable"),
    )
    def test_keyword_fallback_when_classifier_is_unavailable(self, _chat):
        self.assertEqual(classify_agent_intent("请根据课程内容出5道选择题"), "exercise")
        self.assertEqual(classify_agent_intent("帮我总结这一章"), "summary")


class AgentRouteTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = database.DB_PATH
        database.DB_PATH = Path(self.temp_dir.name) / "agent-test.sqlite3"
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

        login = self.client.post(
            "/api/auth/login",
            json={"username": "student01", "password": "Student@123"},
        )
        self.assertEqual(login.status_code, 200)
        payload = login.get_json()
        self.headers = {"Authorization": f"Bearer {payload['token']}"}
        self.user_id = payload["user"]["id"]

        conn = database.get_conn()
        teacher_id = conn.execute(
            "SELECT id FROM users WHERE role = 'teacher' ORDER BY id LIMIT 1"
        ).fetchone()["id"]
        cursor = conn.execute(
            "INSERT INTO classes (name, description, teacher_id, created_at) "
            "VALUES ('测试班级', '', ?, '2026-01-01 09:00:00')",
            (teacher_id,),
        )
        conn.execute(
            "INSERT INTO class_members (class_id, user_id, joined_at) "
            "VALUES (?, ?, '2026-01-01 09:00:00')",
            (cursor.lastrowid, self.user_id),
        )
        conn.commit()
        conn.close()

        classes = self.client.get("/api/classes", headers=self.headers).get_json()["classes"]
        self.class_id = classes[0]["id"]

    def tearDown(self):
        database.DB_PATH = self.original_db_path
        self.temp_dir.cleanup()

    @patch("backend.routers.agent.call_bigmodel_chat", return_value="基于课件的回答")
    @patch("backend.routers.agent.classify_agent_intent", return_value="summary")
    @patch("backend.routers.agent.retrieve_class_knowledge")
    def test_summary_uses_knowledge_route(self, retrieve, _classify, _chat):
        retrieve.return_value = {
            "knowledge_text": "课件知识",
            "sources": [{"courseware_id": 1, "title": "第一讲", "viewer_url": "/preview/1"}],
            "related_coursewares": [{"courseware_id": 1, "title": "第一讲"}],
            "retriever_error": None,
        }
        response = self.client.post(
            "/api/ai/agent",
            json={"class_id": self.class_id, "message": "总结本周课件"},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["intent"], "summary")
        self.assertEqual(payload["route"], "knowledge_base")
        self.assertEqual(payload["sources"][0]["title"], "第一讲")
        self.assertEqual(len(payload["messages"]), 2)

    @patch("backend.routers.agent.classify_agent_intent", return_value="advice")
    def test_advice_prompt_contains_database_history(self, _classify):
        conn = database.get_conn()
        conn.execute(
            "INSERT INTO rag_chat_messages "
            "(class_id, user_id, role, content, sources, created_at) "
            "VALUES (?, ?, 'user', ?, '[]', '2026-01-01 10:00:00')",
            (self.class_id, self.user_id, "我不理解需求分析"),
        )
        conn.commit()
        conn.close()

        captured = {}

        def fake_chat(messages):
            captured["messages"] = messages
            return "个性化建议"

        with patch("backend.routers.agent.call_bigmodel_chat", side_effect=fake_chat):
            response = self.client.post(
                "/api/ai/agent",
                json={"class_id": self.class_id, "message": "给我个性化学习建议"},
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["route"], "personalized")
        self.assertIn("我不理解需求分析", captured["messages"][0]["content"])
        self.assertEqual(payload["sources"][0]["type"], "personal_history")

    def test_agent_messages_require_class_access(self):
        response = self.client.get(
            "/api/ai/agent/messages?class_id=999999", headers=self.headers
        )
        self.assertEqual(response.status_code, 403)

    def test_clear_endpoints_delete_database_records(self):
        conn = database.get_conn()
        conn.execute(
            "INSERT INTO agent_chat_messages "
            "(class_id, user_id, role, content, intent, sources, created_at) "
            "VALUES (?, ?, 'user', '首页问题', 'qa', '[]', '2026-01-01 10:00:00')",
            (self.class_id, self.user_id),
        )
        conn.execute(
            "INSERT INTO rag_chat_messages "
            "(class_id, user_id, role, content, sources, created_at) "
            "VALUES (?, ?, 'user', '知识库问题', '[]', '2026-01-01 10:00:00')",
            (self.class_id, self.user_id),
        )
        conn.commit()
        conn.close()

        agent_response = self.client.delete(
            f"/api/ai/agent/messages?class_id={self.class_id}", headers=self.headers
        )
        rag_response = self.client.delete(
            f"/api/rag/messages?class_id={self.class_id}", headers=self.headers
        )
        self.assertEqual(agent_response.status_code, 200)
        self.assertEqual(rag_response.status_code, 200)

        conn = database.get_conn()
        agent_count = conn.execute(
            "SELECT COUNT(*) AS count FROM agent_chat_messages "
            "WHERE class_id = ? AND user_id = ?",
            (self.class_id, self.user_id),
        ).fetchone()["count"]
        rag_count = conn.execute(
            "SELECT COUNT(*) AS count FROM rag_chat_messages "
            "WHERE class_id = ? AND user_id = ?",
            (self.class_id, self.user_id),
        ).fetchone()["count"]
        conn.close()
        self.assertEqual(agent_count, 0)
        self.assertEqual(rag_count, 0)


if __name__ == "__main__":
    unittest.main()
