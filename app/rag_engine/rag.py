from typing import Any, Dict, Tuple

from llama_index.core import Settings
from llama_index.core.prompts import PromptTemplate

from .helpers import get_query_engine

_CLASSIFIER_PROMPT = (
    "You are an intent classifier for an AI support assistant. "
    "Classify the user's request into one of three categories. "
    "Reply with exactly one word (no punctuation or explanation):\n"
    "- HANDOFF -> the user explicitly wants a human agent or human support.\n"
    "- SMALL_TALK -> the user is greeting, thanking, or making polite conversation that does not need knowledge base lookup.\n"
    "- ANSWER -> all other requests that should be answered with knowledge base context.\n\n"
    "User message: {message}\n"
    "Decision:"
)

_CLASSIFIER_TEMPLATE = PromptTemplate(_CLASSIFIER_PROMPT)

_SMALL_TALK_PROMPT = (
    "You are a friendly customer support assistant. "
    "Respond conversationally and concisely to the user, "
    "keeping the tone warm and professional. "
    "Do not mention that you are a classifier.\n\n"
    "User message: {message}\n"
    "Assistant reply:"
)

_SMALL_TALK_TEMPLATE = PromptTemplate(_SMALL_TALK_PROMPT)


def _classify_intent(message: str) -> str:
    try:
        raw = Settings.llm.predict(_CLASSIFIER_TEMPLATE, message=message)
    except Exception as exc:
        print(f"⚠️ Intent classifier failed: {exc}")
        return "ANSWER"

    normalized = (raw or "").strip().upper()
    if normalized.startswith("HANDOFF"):
        return "HANDOFF"
    if normalized.startswith("SMALL_TALK") or normalized.startswith("SMALL-TALK"):
        return "SMALL_TALK"
    if normalized.startswith("ANSWER"):
        return "ANSWER"

    print(f"⚠️ Intent classifier ambiguous response: {raw!r}")
    return "ANSWER"


def _generate_small_talk(message: str) -> str:
    try:
        reply = Settings.llm.predict(_SMALL_TALK_TEMPLATE, message=message)
    except Exception as exc:
        print(f"⚠️ Small talk generation failed: {exc}")
        return "I'm here to help with anything you need."
    return (reply or "").strip() or "I'm here to help with anything you need."


def initial_state() -> Dict[str, Any]:
    return {}


def handle_input(state: Dict[str, Any], text: str) -> Tuple[Dict[str, Any], str, str]:
    prompt = (text or "").strip()
    if not prompt:
        return state, "Sorry, I didn't catch that. Could you try again?", "ok"

    intent = _classify_intent(prompt)

    if intent == "HANDOFF":
        return state, "human_agent", "handoff"
    if intent == "SMALL_TALK":
        reply = _generate_small_talk(prompt)
        return state, reply, "ok"

    try:
        query_engine = get_query_engine()
        response = query_engine.query(prompt)
        answer = getattr(response, "response", None) or str(response)
        return state, answer.strip(), "ok"
    except Exception as exc:
        return state, f"Internal error: {exc}", "error"
