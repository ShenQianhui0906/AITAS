"""智能测验路由"""

from flask import Blueprint, request, jsonify, g
from backend.middleware.auth import require_auth
from backend.database import get_conn
from backend.models.quiz import (
    create_template, get_template, list_templates_by_class,
    list_templates_by_teacher, delete_template,
    submit_answers, get_submission, get_submission_by_id,
    list_submissions, grade_submission
)
from backend.services.quiz_service import (
    apply_short_answer_reviews,
    auto_grade_submission,
    generate_quiz,
)
from backend.services.notification_service import notify_quiz_published, notify_quiz_graded
from backend.models.access import user_can_access_class, user_can_manage_class

quiz_bp = Blueprint('quiz', __name__)


def _require_teacher():
    if g.current_user['role'] not in ('teacher', 'admin'):
        return jsonify({"error": "仅教师或管理员可执行此操作。"}), 403
    return None


def _get_manageable_quiz(conn, quiz_id):
    quiz = get_template(conn, quiz_id)
    if not quiz:
        return None, (jsonify({"error": "测验不存在"}), 404)
    if not user_can_manage_class(conn, g.current_user, quiz['class_id']):
        return None, (jsonify({"error": "当前账号无权管理该测验。"}), 403)
    return quiz, None


def _submission_payload(submission, questions):
    item = dict(submission)
    details = item.get('details') or []
    if not details:
        details = auto_grade_submission(questions, item.get('answers') or [])['details']

    normalised_details = []
    for raw_detail in details:
        detail = dict(raw_detail)
        index = detail.get('question_index')
        question = questions[index] if isinstance(index, int) and 0 <= index < len(questions) else {}
        question_type = detail.get('question_type') or question.get('type', '')
        detail['question_type'] = question_type
        if question_type == 'short':
            detail['review_status'] = (
                'reviewed' if detail.get('manual_review') else detail.get('review_status', 'pending')
            )
        else:
            detail['review_status'] = 'not_required'
        normalised_details.append(detail)

    total = len(questions)
    score = item.get('score')
    if score is None:
        score = sum(1 for detail in normalised_details if detail.get('correct') is True)
    item['score'] = score
    item['total'] = total
    item['percentage'] = round(score / total * 100, 1) if total else 0
    item['details'] = normalised_details
    item['pending_short_count'] = sum(
        1 for detail in normalised_details
        if detail.get('question_type') == 'short' and detail.get('review_status') != 'reviewed'
    )
    item['reviewed_short_count'] = sum(
        1 for detail in normalised_details
        if detail.get('question_type') == 'short' and detail.get('review_status') == 'reviewed'
    )
    item.pop('answers_json', None)
    item.pop('ai_feedback', None)
    return item


def _quiz_payload(quiz, *, include_answers):
    item = dict(quiz)
    questions = []
    for raw_question in item.get('questions') or []:
        question = dict(raw_question)
        if not include_answers:
            question.pop('answer', None)
            question.pop('explanation', None)
        questions.append(question)
    item['questions'] = questions
    item['question_count'] = len(questions)
    item.pop('questions_json', None)
    return item


@quiz_bp.route('/api/quizzes/generate', methods=['POST'])
@require_auth
def ai_generate():
    """AI 生成测验题目 —— 通过 RAG 检索知识库 + 大模型生成"""
    err = _require_teacher()
    if err: return err
    data = request.get_json(silent=True) or {}
    description = (data.get('description') or '').strip()
    try:
        class_id = int(data.get('class_id'))
    except (TypeError, ValueError):
        return jsonify({"error": "班级编号不合法"}), 400
    question_count = data.get('question_count', 5)
    question_types = data.get('question_types', ['choice', 'truefalse', 'short'])
    difficulty = data.get('difficulty', 'medium')
    if not description:
        return jsonify({"error": "请提供知识范围描述"}), 400
    if not class_id:
        return jsonify({"error": "请提供班级 ID"}), 400

    conn = get_conn()
    try:
        if not user_can_manage_class(conn, g.current_user, class_id):
            return jsonify({"error": "当前账号无权使用该班级知识库出题。"}), 403
    finally:
        conn.close()

    # RAG 检索：从该班级的知识库中检索相关课件内容
    from backend.services.rag_service import query_class_index
    rag_chunks = query_class_index(class_id, description, n_results=5)
    if rag_chunks:
        courseware_text = '\n\n'.join(c['content'] for c in rag_chunks if c.get('content'))
    else:
        courseware_text = description

    questions = generate_quiz(courseware_text, question_count, question_types, difficulty, description)
    return jsonify({'questions': questions}), 200


@quiz_bp.route('/api/quizzes', methods=['POST'])
@require_auth
def publish_quiz():
    """教师发布测验"""
    err = _require_teacher()
    if err: return err
    data = request.get_json(silent=True) or {}
    try:
        class_id = int(data.get('class_id'))
    except (TypeError, ValueError):
        return jsonify({"error": "班级编号不合法"}), 400
    title = (data.get('title') or '').strip()
    questions = data.get('questions', [])
    settings = data.get('settings', {})
    if not title or not questions:
        return jsonify({"error": "缺少必填字段"}), 400
    conn = get_conn()
    try:
        if not user_can_manage_class(conn, g.current_user, class_id):
            return jsonify({"error": "当前账号无权向该班级发布测验。"}), 403
        quiz_id = create_template(conn, g.current_user['id'], class_id, title,
                                  questions, settings)
        notify_quiz_published(
            class_id,
            g.current_user.get('display_name') or g.current_user.get('username') or '教师',
            title,
            quiz_id,
        )
        return jsonify({'quiz_id': quiz_id}), 200
    finally:
        conn.close()


@quiz_bp.route('/api/quizzes', methods=['GET'])
@require_auth
def list_quizzes():
    """获取测验列表"""
    class_id = request.args.get('class_id', type=int)
    conn = get_conn()
    try:
        if class_id:
            if not user_can_access_class(conn, g.current_user, class_id):
                return jsonify({"error": "当前账号无权查看该班级测验。"}), 403
            quizzes = list_templates_by_class(conn, class_id)
        elif g.current_user['role'] == 'teacher':
            quizzes = list_templates_by_teacher(conn, g.current_user['id'])
        else:
            return jsonify({"error": "请指定班级"}), 400
        return jsonify({
            'quizzes': [
                _quiz_payload(
                    quiz,
                    include_answers=user_can_manage_class(
                        conn, g.current_user, quiz['class_id']
                    ),
                )
                for quiz in quizzes
            ]
        }), 200
    finally:
        conn.close()


@quiz_bp.route('/api/quizzes/<int:quiz_id>', methods=['GET'])
@require_auth
def quiz_detail(quiz_id):
    """获取测验详情（含学生自己的提交）"""
    conn = get_conn()
    try:
        quiz = get_template(conn, quiz_id)
        if not quiz:
            return jsonify({"error": "测验不存在"}), 404
        if not user_can_access_class(conn, g.current_user, quiz['class_id']):
            return jsonify({"error": "当前账号无权查看该测验。"}), 403
        submission = None
        if g.current_user['role'] == 'student':
            submission = get_submission(conn, quiz_id, g.current_user['id'])
            if submission:
                submission = _submission_payload(submission, quiz.get('questions', []))
        return jsonify({
            'quiz': _quiz_payload(
                quiz,
                include_answers=user_can_manage_class(
                    conn, g.current_user, quiz['class_id']
                ),
            ),
            'submission': submission,
        }), 200
    finally:
        conn.close()


@quiz_bp.route('/api/quizzes/<int:quiz_id>/submit', methods=['POST'])
@require_auth
def submit_quiz(quiz_id):
    """学生提交测验答案，自动批改"""
    if g.current_user['role'] != 'student':
        return jsonify({"error": "仅学生可以提交测验。"}), 403
    conn = get_conn()
    try:
        quiz = get_template(conn, quiz_id)
        if not quiz:
            return jsonify({"error": "测验不存在"}), 404
        if not user_can_access_class(conn, g.current_user, quiz['class_id']):
            return jsonify({"error": "当前账号无权提交该测验。"}), 403
        data = request.get_json(silent=True) or {}
        answers = data.get('answers', [])
        existing = get_submission(conn, quiz_id, g.current_user['id'])
        if existing:
            return jsonify({"error": "已提交过该测验"}), 400
        result = auto_grade_submission(quiz['questions'], answers)
        sub_id = submit_answers(conn, quiz_id, g.current_user['id'], answers)
        grade_submission(conn, sub_id, result['score'], result['details'])
        notify_quiz_graded(quiz['teacher_id'],
                           g.current_user.get('display_name', '学生'),
                           quiz['title'], quiz_id, result['score'], result['total'])
        return jsonify({
            'submission_id': sub_id,
            'score': result['score'],
            'total': result['total'],
            'percentage': result['percentage'],
            'details': result['details'],
            'pending_short_count': sum(
                1 for detail in result['details']
                if detail.get('question_type') == 'short'
            ),
        }), 200
    finally:
        conn.close()


@quiz_bp.route('/api/quizzes/<int:quiz_id>/grade', methods=['POST'])
@require_auth
def grade_quiz(quiz_id):
    """教师触发批量重新批改"""
    err = _require_teacher()
    if err: return err
    conn = get_conn()
    try:
        quiz, error = _get_manageable_quiz(conn, quiz_id)
        if error:
            return error
        submissions = list_submissions(conn, quiz_id)
        graded_count = 0
        for sub in submissions:
            result = auto_grade_submission(quiz['questions'], sub['answers'])
            existing_reviews = []
            for detail in sub.get('details') or []:
                manual_review = detail.get('manual_review') or {}
                if detail.get('question_type') == 'short' and isinstance(manual_review.get('correct'), bool):
                    existing_reviews.append({
                        'question_index': detail.get('question_index'),
                        'correct': manual_review['correct'],
                        'comment': manual_review.get('comment', ''),
                    })
            if existing_reviews:
                result = apply_short_answer_reviews(
                    quiz['questions'], result['details'], existing_reviews, g.current_user
                )
            grade_submission(conn, sub['id'], result['score'], result['details'])
            graded_count += 1
        return jsonify({'graded_count': graded_count}), 200
    finally:
        conn.close()


@quiz_bp.route('/api/quizzes/<int:quiz_id>/submissions', methods=['GET'])
@require_auth
def quiz_submissions(quiz_id):
    """教师查看测验的全部提交明细。"""
    err = _require_teacher()
    if err:
        return err
    conn = get_conn()
    try:
        quiz, error = _get_manageable_quiz(conn, quiz_id)
        if error:
            return error
        submissions = [
            _submission_payload(submission, quiz['questions'])
            for submission in list_submissions(conn, quiz_id)
        ]
        return jsonify({
            'quiz': _quiz_payload(quiz, include_answers=True),
            'submissions': submissions,
            'summary': {
                'submission_count': len(submissions),
                'pending_review_count': sum(
                    1 for submission in submissions
                    if submission['pending_short_count'] > 0
                ),
                'average_percentage': round(
                    sum(submission['percentage'] for submission in submissions) / len(submissions), 1
                ) if submissions else 0,
            },
        }), 200
    finally:
        conn.close()


@quiz_bp.route(
    '/api/quizzes/<int:quiz_id>/submissions/<int:submission_id>/review',
    methods=['PUT'],
)
@require_auth
def review_short_answers(quiz_id, submission_id):
    """教师人工复核一份答卷中的简答题。"""
    err = _require_teacher()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    conn = get_conn()
    try:
        quiz, error = _get_manageable_quiz(conn, quiz_id)
        if error:
            return error
        submission = get_submission_by_id(conn, submission_id)
        if not submission or submission['quiz_id'] != quiz_id:
            return jsonify({"error": "测验提交记录不存在。"}), 404
        details = _submission_payload(submission, quiz['questions'])['details']
        try:
            result = apply_short_answer_reviews(
                quiz['questions'], details, data.get('reviews'), g.current_user
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        grade_submission(conn, submission_id, result['score'], result['details'])
        updated = get_submission_by_id(conn, submission_id)
        return jsonify({
            'submission': _submission_payload(updated, quiz['questions'])
        }), 200
    finally:
        conn.close()


@quiz_bp.route('/api/quizzes/<int:quiz_id>', methods=['DELETE'])
@require_auth
def delete_quiz(quiz_id):
    """删除测验"""
    err = _require_teacher()
    if err: return err
    conn = get_conn()
    try:
        quiz, error = _get_manageable_quiz(conn, quiz_id)
        if error:
            return error
        delete_template(conn, quiz_id)
        return jsonify({'ok': True}), 200
    finally:
        conn.close()
