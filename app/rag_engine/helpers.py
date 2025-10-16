import json
import os
import re
from pathlib import Path
from string import Template
from typing import Dict, List, Optional, Tuple

import numpy as np
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import BaseMessage
from openai import OpenAI
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ---------------------- Config ----------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY")

client = OpenAI()

# Defaults are cheap/solid; override via env if you want
MODEL_ANSWER = os.getenv("OPENAI_MODEL_ANSWER", "gpt-4o-mini")
MODEL_QUERIES = os.getenv("OPENAI_MODEL_QUERIES", "gpt-4.1-mini")
TOP_K = int(os.getenv("TOP_K", "4"))

KB_PATH = os.getenv(
    "KNOWLEDGE_FILE",
    str((Path(__file__).parent / "kb.txt").resolve())
)

PROMPTS_PATH = os.getenv(
    "PROMPTS_FILE",
    str((Path(__file__).parent / "prompts.json").resolve())
)

PROMPT_KEYS = ("queries", "smalltalk", "answer", "route")


def _load_prompts(path: str) -> Dict[str, str]:
    if not os.path.exists(path):
        raise RuntimeError(f"Prompt template file not found at {path}")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Prompt template file {path} is not valid JSON") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"Prompt template file {path} must contain a JSON object")
    missing = [key for key in PROMPT_KEYS if key not in data]
    if missing:
        raise RuntimeError(f"Prompt template file {path} is missing keys: {', '.join(missing)}")
    prompts: Dict[str, str] = {}
    for key in PROMPT_KEYS:
        value = data[key]
        if isinstance(value, str):
            prompts[key] = value
            continue
        if isinstance(value, list):
            if not all(isinstance(item, str) for item in value):
                raise RuntimeError(f"Prompt template '{key}' in {path} must contain only strings")
            prompts[key] = "\n".join(value)
            continue
        raise RuntimeError(
            f"Prompt template '{key}' in {path} must be a string or list of strings"
        )
    return prompts


_PROMPTS = _load_prompts(PROMPTS_PATH)

def _render_prompt(name: str, **kwargs: object) -> str:
    if name not in _PROMPTS:
        raise KeyError(f"Unknown prompt '{name}' requested")
    template = Template(_PROMPTS[name])
    safe_kwargs = {key: str(value) for key, value in kwargs.items()}
    return template.safe_substitute(**safe_kwargs)

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

    #Create a LangChain conversation memory to track dialogue turns.
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

    #Call OpenAI Responses API and return plain text.
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
        prompt = _render_prompt(
            "queries",
            user_input=user_input,
            memory=_memory_summary(mem),
        )
        lines = _openai_text(MODEL_QUERIES, prompt, max_tokens=80, temperature=0.2).splitlines()
        return [q.strip("-• \t") for q in lines if q.strip()][:5] or [user_input]
    except Exception:
        return [user_input]


def _answer_smalltalk(user_input: str, mem: Optional[ConversationBufferMemory]) -> str:

    #Short, friendly small-talk via OpenAI. One sentence; language-aware.
    history_summary = _memory_summary(mem)
    persona = (
        f"Conversation so far: {history_summary}\nBe friendly, concise, and professional."
        if history_summary != "None"
        else "Be friendly, concise, and professional."
    )
    prompt = _render_prompt(
        "smalltalk",
        persona=persona,
        user_input=user_input,
        memory=history_summary,
    )
    try:
        text = _openai_text(MODEL_QUERIES, prompt, max_tokens=40, temperature=0.7)
        return (text.split("\n")[0] or "Claro! Como posso ajudar?")[:240]
    except Exception:
        return "Claro! Como posso ajudar?"


def _answer_with_openai(user_input: str, mem: Optional[ConversationBufferMemory], context_chunks: List[str]) -> str:
    kb_block = "\n\n---\n\n".join(context_chunks) if context_chunks else "(no KB snippets)"
    prompt = _render_prompt(
        "answer",
        user_input=user_input,
        memory=_memory_summary(mem),
        knowledge_base=kb_block,
    )
    return _openai_text(MODEL_ANSWER, prompt, max_tokens=400, temperature=0.3)


def _route_intent(user_input: str, mem: Optional[ConversationBufferMemory]) -> str:

    #Ask the model to pick exactly one: smalltalk | human | business. Fallback defaults to the business flow if the call fails.
    prompt = _render_prompt(
        "route",
        user_input=user_input,
        memory=_memory_summary(mem),
    )
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
