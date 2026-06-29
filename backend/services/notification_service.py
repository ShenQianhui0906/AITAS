"""通知分发服务。

业务路由只提供事件信息，收件人筛选和批量落库由这里统一处理。
"""

from __future__ import annotations

from backend.database import get_conn
from backend.models.notification import create_notification


def _class_student_ids(conn, class_id: int) -> list[int]:
    rows = conn.execute(
        """
        SELECT cm.user_id
        FROM class_members cm
        JOIN users u ON u.id = cm.user_id
        WHERE cm.class_id = ? AND u.role = 'student'
        ORDER BY cm.user_id
        """,
        (class_id,),
    ).fetchall()
    return [row["user_id"] for row in rows]


def _create_for_recipients(
    recipient_ids: list[int],
    *,
    notif_type: str,
    title: str,
    body: str,
    ref_type: str | None = None,
    ref_id: int | None = None,
) -> int:
    recipients = list(dict.fromkeys(int(user_id) for user_id in recipient_ids if user_id))
    if not recipients:
        return 0

    conn = get_conn()
    try:
        for recipient_id in recipients:
            create_notification(
                conn=conn,
                recipient_id=recipient_id,
                notif_type=notif_type,
                title=title,
                body=body,
                ref_type=ref_type,
                ref_id=ref_id,
                commit=False,
            )
        conn.commit()
        return len(recipients)
    finally:
        conn.close()


def _notify_class_students(class_id: int, **notification) -> int:
    conn = get_conn()
    try:
        student_ids = _class_student_ids(conn, class_id)
    finally:
        conn.close()
    return _create_for_recipients(student_ids, **notification)


def notify_assignment_published(
    class_id: int,
    teacher_name: str,
    assignment_title: str,
    assignment_id: int,
    due_at: str,
) -> int:
    return _notify_class_students(
        class_id,
        notif_type="assignment_published",
        title="新作业发布",
        body=f"{teacher_name} 发布了作业「{assignment_title}」，截止时间 {due_at}",
        ref_type="assignment",
        ref_id=assignment_id,
    )


def notify_quiz_published(
    class_id: int,
    teacher_name: str,
    quiz_title: str,
    quiz_id: int,
) -> int:
    return _notify_class_students(
        class_id,
        notif_type="quiz_published",
        title="新测验发布",
        body=f"{teacher_name} 发布了测验「{quiz_title}」，请及时完成",
        ref_type="quiz",
        ref_id=quiz_id,
    )


def notify_courseware_uploaded(
    class_id: int,
    teacher_name: str,
    courseware_title: str,
    courseware_id: int,
) -> int:
    return _notify_class_students(
        class_id,
        notif_type="courseware_uploaded",
        title="新课件上传",
        body=f"{teacher_name} 上传了课件「{courseware_title}」",
        ref_type="courseware",
        ref_id=courseware_id,
    )


def notify_feedback_received(
    teacher_id: int,
    student_name: str,
    courseware_title: str,
    courseware_id: int,
    suggestion: str = "",
) -> int:
    preview = suggestion.strip()[:80]
    detail = f"：{preview}" if preview else ""
    return _create_for_recipients(
        [teacher_id],
        notif_type="feedback_received",
        title="收到新反馈",
        body=f"{student_name} 对课件「{courseware_title}」提交了反馈{detail}",
        ref_type="feedback",
        ref_id=courseware_id,
    )


def notify_quiz_graded(
    teacher_id: int,
    student_name: str,
    quiz_title: str,
    quiz_id: int,
    score: float,
    total: int,
) -> int:
    return _create_for_recipients(
        [teacher_id],
        notif_type="quiz_graded",
        title="学生完成测验",
        body=f"{student_name} 完成了测验「{quiz_title}」，得分 {score}/{total}",
        ref_type="quiz",
        ref_id=quiz_id,
    )


def notify_courseware_indexed(class_id: int, student_ids: list[int]) -> int:
    return _create_for_recipients(
        student_ids,
        notif_type="courseware_indexed",
        title="知识库已就绪",
        body="班级课件已索引完成，现在可以开始 RAG 问答了",
        ref_type="rag",
        ref_id=class_id,
    )


def notify_assignment_graded(
    student_id: int, assignment_title: str, score: float, assignment_id: int
) -> int:
    return _create_for_recipients(
        [student_id],
        notif_type="assignment_graded",
        title="作业已批改",
        body=f"作业「{assignment_title}」已批改，得分 {score}",
        ref_type="assignment",
        ref_id=assignment_id,
    )


def notify_new_message(
    receiver_id: int, sender_name: str, preview: str, conversation_id: int
) -> int:
    """私信通知发给实际收件人，无论收件人是教师还是学生。"""
    return _create_for_recipients(
        [receiver_id],
        notif_type="new_message",
        title="新私信",
        body=f"{sender_name}：{preview[:50]}",
        ref_type="message",
        ref_id=conversation_id,
    )
