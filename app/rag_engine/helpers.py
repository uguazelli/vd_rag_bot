import os
import re
from typing import List, Optional, Tuple
from pathlib import Path

import numpy as np
from openai import OpenAI
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import BaseMessage

# ---------------------- Config ----------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY")

client = OpenAI()

# Defaults are cheap/solid; override via env if you want
MODEL_ANSWER = os.getenv("OPENAI_MODEL_ANSWER", "gpt-4o-mini")
MODEL_QUERIES = os.getenv("OPENAI_MODEL_QUERIES", "gpt-4.1-mini")

KB_PATH = os.getenv(
    "KNOWLEDGE_FILE",
    str((Path(__file__).parent / "kb.txt").resolve())
)
TOP_K = int(os.getenv("TOP_K", "4"))

# ---------------------- KB in-memory ----------------------
_KB_TEXTS: List[str] = []
_VECTORIZER: TfidfVectorizer | None = None
_KB_MATRIX: np.ndarray | None = None

# ---------------------- KB helpers ----------------------
def _read_txt_chunks(path: str) -> List[str]:
    if not os.path.exists(path):
        return []
    raw = open(path, "r", encoding="utf-8").read()
    parts = [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]
    return parts or [raw.strip()]


def _build_index(texts: List[str]) -> tuple[TfidfVectorizer, np.ndarray]:
    vect = TfidfVectorizer(ngram_range=(1, 2), max_features=50_000)
    mat = vect.fit_transform(texts)
    return vect, mat


def _ensure_kb_loaded() -> None:
    global _KB_TEXTS, _VECTORIZER, _KB_MATRIX
    if _VECTORIZER is None:
        _KB_TEXTS = _read_txt_chunks(KB_PATH) or ["(Knowledge base is empty)"]
        _VECTORIZER, _KB_MATRIX = _build_index(_KB_TEXTS)


def _search(text: str, top_k: int = TOP_K) -> List[Tuple[str, float]]:
    _ensure_kb_loaded()
    q = _VECTORIZER.transform([text])               # type: ignore[union-attr]
    sims = cosine_similarity(q, _KB_MATRIX).ravel() # type: ignore[arg-type]
    idx = np.argsort(-sims)[:top_k]
    return [(_KB_TEXTS[i], float(sims[i])) for i in idx]


# ---------------------- Memory ----------------------
def create_conversation_memory() -> ConversationBufferMemory:
    """
    Create a LangChain conversation memory to track dialogue turns.
    """
    return ConversationBufferMemory(memory_key="history", input_key="input", output_key="output", return_messages=True)


def _format_messages(history: List[BaseMessage]) -> str:
    lines: List[str] = []
    for msg in history[-8:]:
        role = "User" if msg.type == "human" else "Assistant"
        content = msg.content.strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _memory_summary(mem: Optional[ConversationBufferMemory]) -> str:
    if mem is None:
        return "None"
    try:
        data = mem.load_memory_variables({})
    except Exception:
        return "None"
    history = data.get(getattr(mem, "memory_key", "history"))
    if not history:
        return "None"
    if isinstance(history, str):
        return history.strip() or "None"
    if isinstance(history, list):
        return _format_messages(history) or "None"
    return str(history)


# ---------------------- OpenAI helpers ----------------------
def _openai_text(model: str, prompt: str, max_tokens: int = 400, temperature: float = 0.3) -> str:
    """
    Call OpenAI Responses API and return plain text.
    """
    resp = client.responses.create(
        model=model,
        input=prompt,
        max_output_tokens=max_tokens,
        temperature=temperature,
    )
    return (getattr(resp, "output_text", None) or "").strip()


# ---------------------- Generative helpers (OpenAI) ----------------------
def _gen_queries(user_input: str, mem: Optional[ConversationBufferMemory]) -> List[str]:
    try:
        prompt = (
            "Generate 3 to 5 short search queries (one per line) to retrieve useful "
            "snippets from my knowledge base for the user question.\n\n"
            f"User question: {user_input}\n\nUser memory: {_memory_summary(mem)}\n\n"
            "Only output the queries, no bullets, no numbering."
        )
        lines = _openai_text(MODEL_QUERIES, prompt, max_tokens=80, temperature=0.2).splitlines()
        return [q.strip("-• \t") for q in lines if q.strip()][:5] or [user_input]
    except Exception:
        return [user_input]


def _answer_smalltalk(user_input: str, mem: Optional[ConversationBufferMemory]) -> str:
    """
    Short, friendly small-talk via OpenAI. One sentence; language-aware.
    """
    history_summary = _memory_summary(mem)
    persona = (f"Conversation so far: {history_summary}\n" if history_summary != "None" else "") + "Be friendly, concise, and professional."
    prompt = f"""
                You are a helpful support assistant doing small talk. {persona}
                Requirements:
                - Reply in the same language as the user message below.
                - Keep it to ONE short sentence (<= 18 words).
                - Be warm and natural; 0–1 emoji max.
                - Do NOT reference any knowledge base.
                - If the user says thanks, offer help once.
                User message: {user_input}
                """.strip()
    try:
        text = _openai_text(MODEL_QUERIES, prompt, max_tokens=40, temperature=0.7)
        return (text.split("\n")[0] or "Claro! Como posso ajudar?")[:240]
    except Exception:
        return "Claro! Como posso ajudar?"


def _answer_with_openai(user_input: str, mem: Optional[ConversationBufferMemory], context_chunks: List[str]) -> str:
    kb_block = "\n\n---\n\n".join(context_chunks) if context_chunks else "(no KB snippets)"
    prompt = f"""
                You are an assistant that must answer using the Knowledge Base excerpts and the conversation memory.
                - Use the Knowledge Base for product/policy/support facts.
                - Use the conversation memory for personalization or questions about prior dialogue.
                - If neither source gives the answer, say you don't have enough info and suggest talking to a human.

                User message:
                \"\"\"{user_input}\"\"\"

                Conversation memory (if helpful):
                {_memory_summary(mem)}

                Knowledge Base excerpts:
                {kb_block}

                Instructions:
                - Be concise and clear.
                - If user explicitly asks to talk to a human, do NOT answer: return the token HUMAN_AGENT.
                - If the KB does not cover the answer, say so briefly and suggest a human handoff.
                """.strip()
    return _openai_text(MODEL_ANSWER, prompt, max_tokens=400, temperature=0.3)


def _route_intent(user_input: str, mem: Optional[ConversationBufferMemory]) -> str:
    """
    Ask the model to pick exactly one: smalltalk | human | business.
    Fallback defaults to the business flow if the call fails.
    """
    prompt = f"""
            Classify the user's message into exactly ONE of these intents:
            - smalltalk: greetings, thanks, pleasantries, emojis, chit-chat.
            - human: they want to talk to a human/agent/sales/support.
            - business: a product/pricing/support/use-case question that needs KB/RAG.

            Return only one token: smalltalk | human | business.
            User: {user_input}
            Known: {_memory_summary(mem)}
            """.strip()
    try:
        label = (_openai_text(MODEL_QUERIES, prompt, max_tokens=5, temperature=0.1) or "").strip().lower()
        if label.startswith("small"):
            return "smalltalk"
        if label.startswith("human"):
            return "human"
        if label.startswith("bus"):
            return "business"
    except Exception:
        pass

    # Fallback: default to business flow if classification fails
    return "business"
