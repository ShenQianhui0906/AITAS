"""Intent recognition and personalised prompt construction for the homepage agent."""
from __future__ import annotations

import json
import re

from backend.config import MAX_AI_CONTEXT_CHARS
from backend.services.ai_service import call_bigmodel_chat


VALID_INTENTS = {"qa", "summary", "exercise", "homework", "history", "advice"}
KNOWLEDGE_INTENTS = {"qa", "summary"}
PERSONAL_HISTORY_SOURCE = {
    "type": "personal_history",
    "label": "基于你的历史提问记录生成",
}


def _keyword_intent(question: str) -> str:
    text = (question or "").lower()
    patterns = (
        ("summary", r"总结|概括|大纲|摘要|归纳|梳理"),
        ("exercise", r"练习|题目|习题|测试|出题|考题|选择题|填空题|简答题"),
        ("homework", r"作业|任务|提交|截止|deadline"),
        ("history", r"历史|记录|之前|上次|回顾|学过|问过"),
        ("advice", r"建议|推荐|方法|计划|怎么学|如何学|薄弱|提升|复习安排"),
    )
    for intent, pattern in patterns:
        if re.search(pattern, text):
            return intent
    return "qa"


def _parse_intent(raw_response: str) -> str | None:
    text = (raw_response or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    try:
        payload = json.loads(text)
        intent = payload.get("intent") if isinstance(payload, dict) else payload
    except json.JSONDecodeError:
        match = re.search(r"\b(qa|summary|exercise|homework|history|advice)\b", text)
        intent = match.group(1) if match else None
    return intent if intent in VALID_INTENTS else None


def classify_agent_intent(question: str) -> str:
    """Classify on the server; fall back to deterministic keywords if needed."""
    messages = [
        {
            "role": "system",
            "content": (
                "你是课程助教的意图分类器。只输出 JSON，例如 {\"intent\":\"qa\"}。"
                "可选意图：qa=检索或解释课程知识；summary=总结课程/课件；"
                "exercise=根据课程出题或测验；homework=查询作业任务；"
                "history=回顾个人学习/提问记录；advice=个性化学习建议或计划。"
                "不得回答用户问题本身。"
            ),
        },
        {"role": "user", "content": question},
    ]
    try:
        intent = _parse_intent(
            call_bigmodel_chat(messages, temperature=0.0, max_tokens=64)
        )
    except RuntimeError:
        intent = None
    return intent or _keyword_intent(question)


def list_historical_questions(
    conn,
    user_id: int,
    class_id: int,
    limit: int = 20,
) -> list[dict]:
    """Collect this student's previous questions from all AI entry points."""
    rows = conn.execute(
        """
        SELECT content, created_at, channel FROM (
            SELECT content, created_at, '首页助教' AS channel
            FROM agent_chat_messages
            WHERE user_id = ? AND class_id = ? AND role = 'user'
            UNION ALL
            SELECT content, created_at, '知识库' AS channel
            FROM rag_chat_messages
            WHERE user_id = ? AND class_id = ? AND role = 'user'
            UNION ALL
            SELECT m.content, m.created_at, '课件问答' AS channel
            FROM ai_chat_messages m
            JOIN coursewares cw ON cw.id = m.courseware_id
            WHERE m.user_id = ? AND cw.class_id = ? AND m.role = 'user'
        )
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (user_id, class_id, user_id, class_id, user_id, class_id, limit),
    ).fetchall()
    return [dict(row) for row in reversed(rows)]


def build_personalized_messages(
    *,
    question: str,
    intent: str,
    user: dict,
    class_info: dict,
    historical_questions: list[dict],
    conversation_history: list[dict] | None = None,
) -> list[dict]:
    history_text = "\n".join(
        f"- [{item['created_at']} · {item['channel']}] {item['content']}"
        for item in historical_questions
    )
    if not history_text:
        history_text = "（暂无历史提问记录）"
    history_text = history_text[-MAX_AI_CONTEXT_CHARS:]

    intent_instructions = {
        "exercise": (
            "请结合该学生历史上关注或容易困惑的知识点设计练习题。"
            "题目应有清晰难度层次；除非学生明确要求，否则将答案与解析放在题目之后。"
        ),
        "advice": (
            "请从历史提问中归纳学习关注点，再给出具体、可执行、分优先级的个性化建议。"
        ),
        "history": "请忠实回顾历史提问所反映的学习轨迹，不要虚构学习行为或成绩。",
        "homework": (
            "系统没有独立的作业与截止日期数据。只能依据下方历史提问回答；"
            "若记录不足，请明确说明，不能编造作业或日期。"
        ),
    }
    task_instruction = intent_instructions.get(
        intent,
        "请参考历史提问给出与该学生情况相关的回答。",
    )
    system_prompt = (
        "你是AITAS（AI教学助手），正在提供基于学生历史提问的个性化学习支持。"
        "历史提问只表示学生曾关注的内容，不能据此虚构其成绩、能力或已完成事项。"
        "信息不足时要直接说明，并给出下一步可执行建议。\n\n"
        f"【学生】{user.get('display_name') or user.get('username') or '当前学生'}\n"
        f"【当前班级】{class_info.get('name') or '当前班级'}\n"
        f"【任务要求】{task_instruction}\n\n"
        f"【该学生的历史提问】\n{history_text}"
    )

    messages = [{"role": "system", "content": system_prompt}]
    for message in conversation_history or []:
        role = "assistant" if message.get("role") == "assistant" else "user"
        messages.append({"role": role, "content": message.get("content", "")})
    messages.append({"role": "user", "content": question})
    return messages
