"""
AI Service — LLM API calls (智谱 GLM / BigModel).
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from backend.config import BIGMODEL_API_URL, BIGMODEL_MODEL


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


def call_bigmodel_chat(messages: list[dict]) -> str:
    """Call the BigModel chat API. Returns the assistant's response text.
    Raises RuntimeError on failure."""
    api_key = os.environ.get("BIGMODEL_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("服务器未配置 BIGMODEL_API_KEY，暂时无法使用 AI 问答。")

    payload = {
        "model": BIGMODEL_MODEL,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 2048,
        "thinking": {"type": "disabled"},
    }
    request = urllib.request.Request(
        BIGMODEL_API_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="ignore")
        try:
            err_payload = json.loads(detail)
        except json.JSONDecodeError:
            err_payload = None
        message = parse_bigmodel_error(err_payload) or f"模型服务调用失败（HTTP {error.code}）。"
        raise RuntimeError(message) from error
    except urllib.error.URLError as error:
        raise RuntimeError("模型服务暂时不可用，请稍后再试。") from error

    try:
        content = extract_bigmodel_answer(data["choices"][0]["message"])
    except (KeyError, IndexError, TypeError) as error:
        raise RuntimeError("模型返回格式异常，暂时无法生成回答。") from error

    if not content:
        raise RuntimeError("模型未返回有效内容，请稍后重试。")
    return content
