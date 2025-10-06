import re
import time
from typing import Any, Dict, List

from app.helpers import (
    TOP_K,
    _answer_smalltalk,
    _answer_with_openai,
    _ensure_kb_loaded,
    _gen_queries,
    _route_intent,
    _search,
    _update_memory,
)


def initial_state() -> Dict[str, Any]:
    _ensure_kb_loaded()
    return {"current": "rag", "history": [], "memory": {}, "last_seen_at": time.time()}

def handle_input(state: Dict[str, Any], text: str) -> tuple[Dict[str, Any], str, str]:
    try:
        user = (text or "").strip()
        _update_memory(state.setdefault("memory", {}), user)

        # Intent router
        intent = _route_intent(user, state["memory"])

        if intent == "human":
            return state, "human_agent", "ok"

        if intent == "smalltalk":
            reply = _answer_smalltalk(user, state["memory"])
            hist: List[tuple[str, str, float]] = state.setdefault("history", [])
            hist.append(("user", user, time.time()))
            hist.append(("bot", reply, time.time()))
            state["history"] = hist[-12:]
            state["last_seen_at"] = time.time()
            return state, reply, "ok"

        # intent == "business" → RAG path
        queries = _gen_queries(user, state["memory"])
        seen: set[str] = set()
        retrieved: list[tuple[str, float]] = []
        for q in [user] + queries:
            for chunk, score in _search(q, top_k=TOP_K):
                if chunk not in seen:
                    seen.add(chunk)
                    retrieved.append((chunk, score))
        retrieved.sort(key=lambda x: -x[1])
        context_chunks = [c for c, _ in retrieved[:TOP_K]]

        reply = _answer_with_openai(user, state["memory"], context_chunks)
        if re.search(r"\bHUMAN[_\s-]?AGENT\b", reply, re.IGNORECASE):
            reply = "human_agent"

        hist: List[tuple[str, str, float]] = state.setdefault("history", [])
        hist.append(("user", user, time.time()))
        hist.append(("bot", reply, time.time()))
        state["history"] = hist[-12:]
        state["last_seen_at"] = time.time()
        return state, reply, "ok"

    except Exception as e:
        return state, f"Erro interno: {e}", "error"
