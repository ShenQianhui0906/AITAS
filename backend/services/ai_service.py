"""
AI Service — LLM API calls (智谱 GLM / BigModel).
"""
from __future__ import annotations

import os

import requests

from backend.config import API_URL, MODEL_NAME


def stringify_model_content(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if not text and isinstance(item.get("content"), str):
                    text = item["content"]
                if text:
                    parts.append(str(text))
        return "\n".join(p.strip() for p in parts if str(p).strip()).strip()
    return str(content).strip() if content is not None else ""


def extract_bigmodel_answer(message: dict) -> str:
    if not isinstance(message, dict):
        return ""
    content = stringify_model_content(message.get("content"))
    if content:
        return content
    return stringify_model_content(message.get("reasoning_content"))


def parse_bigmodel_error(payload) -> str | None:
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            return error.get("message") or error.get("code")
        if isinstance(error, str):
            return error
        return payload.get("message")
    return None


def call_bigmodel_chat(
    messages: list[dict], *, temperature: float = 0.3, max_tokens: int = 2048
) -> str:
    """Call the BigModel chat API. Returns the assistant's response text.
    Raises RuntimeError on failure."""
    api_key = os.environ.get("API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("服务器未配置 API_KEY，暂时无法使用 AI 问答。")

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "thinking": {"type": "disabled"},
    }
    try:
        response = requests.post(
            API_URL,
            json=payload,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            timeout=90,
        )
    except requests.exceptions.Timeout as error:
        raise RuntimeError("模型服务响应超时，请稍后重试。") from error
    except requests.exceptions.RequestException as error:
        raise RuntimeError("模型服务暂时不可用，请稍后再试。") from error

    try:
        data = response.json()
    except ValueError as error:
        raise RuntimeError("模型返回格式异常，暂时无法生成回答。") from error

    if response.status_code >= 400:
        message = parse_bigmodel_error(data) or f"模型服务调用失败（HTTP {response.status_code}）。"
        raise RuntimeError(message)

    if not isinstance(data, dict):
        raise RuntimeError("模型返回格式异常，暂时无法生成回答。")

    try:
        content = extract_bigmodel_answer(data["choices"][0]["message"])
    except (KeyError, IndexError, TypeError) as error:
        raise RuntimeError("模型返回格式异常，暂时无法生成回答。") from error

    if not content:
        raise RuntimeError("模型未返回有效内容，请稍后重试。")
    return content
