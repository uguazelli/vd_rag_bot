"""Helpers for interacting with llama-index LLM interfaces."""

from __future__ import annotations

from typing import Any, Iterable, Optional

from llama_index.core.llms import ChatMessage, MessageRole


async def chat_completion(
    llm: Any,
    user_prompt: str,
    *,
    system_prompt: Optional[str] = None,
) -> str:
    """
    Execute a chat completion using llama-index LLM abstraction.

    Falls back to `apredict` when the model does not expose chat semantics.
    """
    if llm is None:
        raise ValueError("LLM instance is required for chat completion.")

    messages: list[ChatMessage] = []
    if system_prompt:
        messages.append(ChatMessage(role=MessageRole.SYSTEM, content=system_prompt))
    messages.append(ChatMessage(role=MessageRole.USER, content=user_prompt))

    if hasattr(llm, "achat"):
        result = await llm.achat(messages)  # type: ignore[attr-defined]
        content = _extract_content(result)
        return content

    # Fallback: models like CompletionLLM only accept plain prompts.
    prompt = f"{system_prompt or ''}\n{user_prompt}".strip()
    result = await llm.apredict(prompt)  # type: ignore[attr-defined]
    return _extract_content(result)


def _extract_content(result: Any) -> str:
    if result is None:
        return ""
    if isinstance(result, str):
        return result
    # ChatResponse from llama-index exposes .message.content or .text
    message = getattr(result, "message", None)
    if message is not None:
        content = getattr(message, "content", None)
        if isinstance(content, str):
            return content
    text = getattr(result, "text", None)
    if isinstance(text, str):
        return text
    return str(result)
