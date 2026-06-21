"""
Pydantic schemas for request/response validation.
Using plain dicts for simplicity with the current http.server approach.
FastAPI can be layered on top later.
"""
from __future__ import annotations

# Auth schemas
# LoginRequest: {username: str, password: str}
# RegisterRequest: {username: str, display_name: str, password: str, role: str, student_number?: str}
# TokenResponse: {token: str, user: dict}

# User schemas
# UserResponse: {id, username, display_name, role, student_number, created_at}
# UserCreate: {username, display_name, role, password, student_number?}
# UserUpdate: {username?, display_name?, role?, password?, student_number?}

# Class schemas
# ClassCreate: {name: str, description?: str, teacher_id?: int}
# ClassUpdate: {name?: str, description?: str, teacher_id?: int}
# ClassResponse: {id, name, description, teacher_id, teacher_name, student_count, created_at}

# Courseware schemas
# CoursewareCreate: {title: str, course_name: str, description?: str, class_id: int, file: bytes}
# CoursewareUpdate: {title?: str, course_name?: str, description?: str}

# Evaluation schemas
# EvaluationCreate: {courseware_id: int, helpfulness: int, usability: int, suitability?: int, practicality?: int, suggestion?: str}

# Discussion schemas
# DiscussionCreate: {title: str, body: str, class_id: int}
# ReplyCreate: {body: str}

# Message schemas
# MessageSend: {receiver_id: int, body: str}
# ConversationCreate: {user_id: int}

# AI Chat schemas
# AiChatRequest: {courseware_id: int, question: str}
# RagChatRequest: {class_id: int, question: str}
