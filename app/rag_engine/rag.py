"""Orchestrates the RAG pipeline for chat interactions."""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from llama_index.core import Settings

from .helpers import configure_llm_from_config, get_query_engine
from .rag_handleInput import classify_user_message
from .rag_llm import chat_completion
from .rag_memory import MemoryState


def initial_state() -> MemoryState:
    return MemoryState()


async def handle_input(
    state: MemoryState,
    user_message: str,
    tenant_id: int,
    *,
    runtime_config: Optional[Dict[str, Any]] = None,
) -> Tuple[MemoryState, str, str]:
    config = runtime_config or {}
    llm_params = configure_llm_from_config(config)

    if state.tenant_id is None:
        state.tenant_id = tenant_id

    llm = getattr(Settings, "llm", None)
    intent, reason = await classify_user_message(llm, state, user_message)

    state.remember("user", user_message)

    if intent == "smalltalk":
        reply: str
        if llm:
            system_prompt = llm_params.get(
                "smalltalk_system_prompt",
                "You are a warm, professional assistant. Reply concisely in the same language as the user.",
            )
            user_prompt = (
                f"Conversation to date:\n{state.transcript() or '(no history)'}\n\n"
                f"Most recent user message:\n{user_message}"
            )
            try:
                reply = await chat_completion(llm, user_prompt, system_prompt=system_prompt)
            except Exception:
                reply = llm_params.get(
                    "smalltalk_reply",
                    "Hello! How can I assist you today?",
                )
        else:
            reply = llm_params.get(
                "smalltalk_reply",
                "Hello! How can I assist you today?",
            )
        state.remember("assistant", reply)
        return state, reply, "smalltalk"

    if intent == "handoff":
        return state, "human_agent", "handoff"

    query_engine = await get_query_engine(
        account_id=int(config.get("omnichannel_id", tenant_id)),
        tenant_id=state.tenant_id,
        runtime_config=config,
        llm_params=llm_params,
    )

    response = query_engine.query(user_message)
    answer = getattr(response, "response", None) or str(response)
    reply = answer.strip()
    if not reply or reply.lower() == "empty response":
        if llm:
            system_prompt = (
                "You are a helpful assistant. Use the conversation history and any known facts to answer the user's latest message. "
                "If the information was previously provided by the user in the conversation, recall it. "
                "If you truly don't know, say so politely."
            )
            user_prompt = (
                f"Conversation so far:\n{state.transcript() or '(no history)'}\n\n"
                f"Latest user message:\n{user_message}"
            )
            try:
                reply = await chat_completion(llm, user_prompt, system_prompt=system_prompt)
            except Exception:
                reply = ""
        if not reply:
            reply = "I couldn't find information related to that yet."
    state.remember("assistant", reply)

    return state, reply, "rag"
