from typing import Any, Dict, Tuple

from .helpers import get_query_engine


def initial_state() -> Dict[str, Any]:
    return {}


def handle_input(state: Dict[str, Any], text: str) -> Tuple[Dict[str, Any], str, str]:
    prompt = (text or "").strip()
    if not prompt:
        return state, "Sorry, I didn't catch that. Could you try again?", "ok"

    try:
        query_engine = get_query_engine()
        response = query_engine.query(prompt)
        answer = getattr(response, "response", None) or str(response)
        return state, answer.strip(), "ok"
    except Exception as exc:
        return state, f"Internal error: {exc}", "error"
