from __future__ import annotations
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional
from llama_index.core import Settings, StorageContext, load_index_from_storage
from llama_index.core.postprocessor.llm_rerank import LLMRerank
from llama_index.core.query_engine.retriever_query_engine import RetrieverQueryEngine
from llama_index.core.response_synthesizers import get_response_synthesizer
from llama_index.core.retrievers.fusion_retriever import QueryFusionRetriever
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI

from app.db.repository import get_params_by_omnichannel_id


DEFAULT_MODEL_ANSWER = "gpt-4o-mini"
DEFAULT_EMBED_MODEL = "text-embedding-3-small"
DEFAULT_TEMPERATURE = 0.1
DEFAULT_TOP_K = 4
DEFAULT_MULTI_QUERY = 3
DEFAULT_RERANK_TOP_N = 5
DEFAULT_RETRIEVER_CANDIDATES = 10

DEFAULT_STORAGE_DIR = Path(__file__).parent / "storage"
PERSIST_DIR = (
    Path(os.getenv("RAG_PERSIST_DIR")).expanduser().resolve()
    if os.getenv("RAG_PERSIST_DIR")
    else (DEFAULT_STORAGE_DIR / "vector_store").resolve()
)


def _parse_params(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return {}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            raise RuntimeError(f"Invalid JSON payload in tenant LLM params: {raw!r}")
    return {}


def _coerce_int(value: Any, fallback: int) -> int:
    try:
        parsed = int(value)
        if parsed > 0:
            return parsed
    except (TypeError, ValueError):
        pass
    return fallback


def _coerce_float(value: Any, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _configure_models(config: Dict[str, Any]) -> Dict[str, Any]:
    llm_params = _parse_params(config.get("llm_params"))

    api_key = config.get("llm_api_key") or llm_params.get("api_key")
    if not api_key:
        raise RuntimeError("Tenant LLM configuration missing required OpenAI API key.")

    model_answer = llm_params.get("model_answer") or DEFAULT_MODEL_ANSWER
    embed_model = llm_params.get("openai_embed_model") or DEFAULT_EMBED_MODEL
    temperature = _coerce_float(llm_params.get("temperature"), DEFAULT_TEMPERATURE)

    Settings.llm = OpenAI(api_key=api_key, model=model_answer, temperature=temperature)
    Settings.embed_model = OpenAIEmbedding(api_key=api_key, model=embed_model)

    return llm_params


@lru_cache(maxsize=1)
def _load_index():
    persist_dir = PERSIST_DIR
    if not persist_dir.exists():
        raise RuntimeError(
            f"No persisted index found at {persist_dir}. "
            "Run the ingestion CLI to create the vector store."
        )
    storage_context = StorageContext.from_defaults(persist_dir=str(persist_dir))
    return load_index_from_storage(storage_context)


async def load_runtime_config(account_id: int) -> Dict[str, Any]:
    cached_params = await get_params_by_omnichannel_id(account_id)
    if not cached_params:
        raise RuntimeError(
            f"No tenant configuration found for omnichannel id {account_id}"
        )
    return cached_params


def configure_llm_from_config(config: Dict[str, Any]) -> Dict[str, Any]:
    return _configure_models(config)


async def get_query_engine(
    account_id: int,
    *,
    runtime_config: Optional[Dict[str, Any]] = None,
    llm_params: Optional[Dict[str, Any]] = None,
) -> RetrieverQueryEngine:
    config = runtime_config or await load_runtime_config(account_id)
    runtime_llm_params = llm_params or _configure_models(config)

    top_k = _coerce_int(runtime_llm_params.get("top_k"), DEFAULT_TOP_K)
    retriever_candidates = _coerce_int(
        runtime_llm_params.get("retriever_candidates"),
        max(DEFAULT_RETRIEVER_CANDIDATES, top_k),
    )
    candidate_pool = max(top_k, retriever_candidates)
    rerank_top_n = _coerce_int(
        runtime_llm_params.get("rerank_top_n"),
        max(DEFAULT_RERANK_TOP_N, min(candidate_pool, top_k)),
    )
    rerank_top_n = min(rerank_top_n, candidate_pool)
    multi_query = _coerce_int(
        runtime_llm_params.get("multi_query_count"), DEFAULT_MULTI_QUERY
    )

    index = _load_index()
    base_retriever = index.as_retriever(similarity_top_k=candidate_pool)

    fusion_retriever = QueryFusionRetriever(
        retrievers=[base_retriever],
        llm=Settings.llm,
        similarity_top_k=candidate_pool,
        num_queries=multi_query,
        verbose=False,
    )

    reranker = LLMRerank(llm=Settings.llm, top_n=rerank_top_n)

    response_synthesizer = get_response_synthesizer(
        llm=Settings.llm,
        response_mode="compact",
    )

    return RetrieverQueryEngine(
        retriever=fusion_retriever,
        node_postprocessors=[reranker],
        response_synthesizer=response_synthesizer,
    )
