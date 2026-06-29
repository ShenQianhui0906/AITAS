"""智能测验服务 - AI 生成题目 / 自动批改"""

import json
import re
from datetime import datetime
from backend.config import MODEL_NAME
from backend.services.ai_service import call_bigmodel_chat


def generate_quiz(courseware_text, question_count=5, question_types=None, difficulty='medium', topic_hint=''):
    """根据知识库内容 AI 生成测验题目
    
    Args:
        courseware_text: 从 RAG 检索到的课件/knowledge base 文本
        question_count: 题目数量
        question_types: 题型列表 ['choice', 'truefalse', 'short']
        difficulty: 难度 easy/medium/hard
        topic_hint: 教师输入的描述/标题，用于聚焦出题范围
    
    Returns:
        list[dict]: 题目列表，每道题包含 type/question/options/answer/explanation
    """
    if not question_types:
        question_types = ['choice', 'truefalse', 'short']
    
    types_desc = {
        'choice': '单选题（4个选项 A/B/C/D）',
        'truefalse': '判断题（正确/错误）',
        'short': '简答题（一句话作答）'
    }
    type_list = ', '.join(types_desc[t] for t in question_types if t in types_desc)
    
    topic_line = f'本次测验聚焦：{topic_hint}' if topic_hint else ''
    
    prompt = f"""你是一位教学经验丰富的教师。请根据以下课件/知识库内容，生成 {question_count} 道测验题目。

【出题范围】
{topic_line}

【知识库内容】
{courseware_text[:6000]}

【要求】
1. 题型包含：{type_list}
2. 难度：{difficulty}
3. 题目应覆盖上述知识库的核心知识点，紧扣出题范围
4. 每道题需提供正确答案和解析
5. 单选题严格要求：4个选项中必须有且仅有1个正确选项（answer 字段只能填单个字母如 "A"），其余3个必须是明确错误但合理的干扰项，绝不能出现多个正确答案或模棱两可的选项

请严格按以下 JSON 格式返回（只返回 JSON，不要其他文字）：
```json
[
  {{
    "type": "choice",
    "question": "题目内容",
    "options": ["A. 唯一的正确选项", "B. 明确的错误选项", "C. 明确的错误选项", "D. 明确的错误选项"],
    "answer": "A",
    "explanation": "解析说明，说明为什么 A 正确、BCD 错在哪里"
  }},
  {{
    "type": "truefalse",
    "question": "题目内容",
    "answer": true,
    "explanation": "解析说明"
  }},
  {{
    "type": "short",
    "question": "题目内容",
    "answer": "参考答案",
    "explanation": "解析说明"
  }}
]
```"""

    raw = call_bigmodel_chat(
        [{"role": "user", "content": prompt}],
        temperature=0.7, max_tokens=4000
    )
    
    # 尝试提取 JSON
    try:
        # 尝试直接解析
        questions = json.loads(raw)
        if isinstance(questions, list):
            return questions[:question_count]
    except json.JSONDecodeError:
        pass
    
    # 尝试从 markdown 代码块提取
    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw)
    if match:
        try:
            questions = json.loads(match.group(1))
            if isinstance(questions, list):
                return questions[:question_count]
        except json.JSONDecodeError:
            pass
    
    # 尝试找到最外层的 [ ... ]
    match = re.search(r'\[\s*\{[\s\S]*\}\s*\]', raw)
    if match:
        try:
            questions = json.loads(match.group(0))
            if isinstance(questions, list):
                return questions[:question_count]
        except json.JSONDecodeError:
            pass
    
    return []


def auto_grade_submission(questions, answers):
    """自动批改学生提交的答案
    
    Args:
        questions: 题目列表（含正确答案）
        answers: 学生提交的答案列表 [{"question_index": 0, "answer": "A"}, ...]
    
    Returns:
        dict: {score, total, percentage, details: [{correct, expected, given, explanation}]}
    """
    if not questions:
        return {'score': 0, 'total': 0, 'percentage': 0, 'details': []}
    
    total = len(questions)
    correct_count = 0
    details = []
    
    # 构建答案映射
    answer_map = {}
    for a in answers:
        idx = a.get('question_index', -1)
        if idx >= 0:
            answer_map[idx] = a.get('answer', '')
    
    for i, q in enumerate(questions):
        expected = q.get('answer', '')
        given = answer_map.get(i, '')
        
        question_type = q.get('type', '')
        # 简答题先给出自动初判，并始终进入教师人工复核队列。
        is_correct = _check_answer(expected, given, question_type)
        
        if is_correct:
            correct_count += 1
        
        details.append({
            'question_index': i,
            'question_type': question_type,
            'correct': is_correct,
            'expected': expected,
            'given': given,
            'explanation': q.get('explanation', ''),
            'review_status': 'pending' if question_type == 'short' else 'not_required',
            'manual_review': None,
        })
    
    score = correct_count
    percentage = round(correct_count / total * 100, 1) if total > 0 else 0
    
    return {
        'score': score,
        'total': total,
        'percentage': percentage,
        'details': details
    }


def _check_answer(expected, given, qtype):
    """判断答案是否正确"""
    if qtype == 'choice':
        # 单选题：比较选项字母
        exp = str(expected).strip().upper().lstrip('ABCD.')
        giv = str(given).strip().upper().lstrip('ABCD.')
        return exp == giv
    elif qtype == 'multi_choice':
        return _normalise_multi_answer(expected) == _normalise_multi_answer(given)
    elif qtype == 'truefalse':
        # 判断题：比较布尔值
        exp = str(expected).strip().lower()
        giv = str(given).strip().lower()
        true_vals = ('true', '正确', '对', 'yes', 't', '1')
        false_vals = ('false', '错误', '错', 'no', 'f', '0')
        if exp in true_vals and giv in true_vals:
            return True
        if exp in false_vals and giv in false_vals:
            return True
        return False
    elif qtype == 'short':
        # 简答题：简单模糊匹配
        exp_clean = str(expected).strip().lower().rstrip('.。')
        giv_clean = str(given).strip().lower().rstrip('.。')
        if exp_clean == giv_clean:
            return True
        # 关键词包含
        if len(exp_clean) <= 20 and exp_clean in giv_clean:
            return True
        if len(giv_clean) <= 20 and giv_clean in exp_clean:
            return True
        return False
    else:
        return str(expected).strip() == str(given).strip()


def _normalise_multi_answer(value) -> set[str]:
    if isinstance(value, (list, tuple, set)):
        parts = value
    else:
        parts = re.split(r"[,，、;；\s]+", str(value or ""))
    return {
        str(part).strip().upper().rstrip(".、")
        for part in parts
        if str(part).strip()
    }


def apply_short_answer_reviews(
    questions: list[dict],
    details: list[dict],
    reviews: list[dict],
    reviewer: dict,
) -> dict:
    """应用教师对简答题的人工判定并重新计算整份答卷分数。"""
    if not isinstance(reviews, list) or not reviews:
        raise ValueError("请至少提交一项简答题复核结果。")

    updated_details = [dict(item) for item in details]
    detail_map = {
        item.get("question_index"): item
        for item in updated_details
        if isinstance(item, dict)
    }
    reviewed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for review in reviews:
        if not isinstance(review, dict):
            raise ValueError("复核数据格式不合法。")
        try:
            question_index = int(review.get("question_index"))
        except (TypeError, ValueError) as exc:
            raise ValueError("复核题目编号不合法。") from exc
        if question_index < 0 or question_index >= len(questions):
            raise ValueError("复核题目不存在。")
        if questions[question_index].get("type") != "short":
            raise ValueError("仅简答题支持人工复核。")
        if not isinstance(review.get("correct"), bool):
            raise ValueError("请选择该简答题判定为正确或错误。")

        detail = detail_map.get(question_index)
        if detail is None:
            raise ValueError("该题缺少自动批改记录，无法复核。")
        comment = str(review.get("comment") or "").strip()
        if len(comment) > 500:
            raise ValueError("单题复核备注不能超过 500 个字符。")
        detail["correct"] = review["correct"]
        detail["review_status"] = "reviewed"
        detail["manual_review"] = {
            "correct": review["correct"],
            "comment": comment,
            "reviewer_id": reviewer.get("id"),
            "reviewer_name": reviewer.get("display_name") or reviewer.get("username") or "教师",
            "reviewed_at": reviewed_at,
        }

    score = sum(1 for item in updated_details if item.get("correct") is True)
    total = len(questions)
    return {
        "score": score,
        "total": total,
        "percentage": round(score / total * 100, 1) if total else 0,
        "details": updated_details,
    }
