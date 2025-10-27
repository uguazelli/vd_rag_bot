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

from app.config import settings


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


def _configure_models(tenant: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if tenant is None:
        Settings.llm = OpenAI(
            api_key=settings.openai_api_key,
            model=settings.openai_model_answer,
            temperature=0.1,
        )
        Settings.embed_model = OpenAIEmbedding(
            api_key=settings.openai_api_key,
            model=settings.openai_embed_model,
        )
        return {}

    llm_config = tenant.get("llm") or {}
    params = _parse_params(llm_config.get("params"))

    api_key = llm_config.get("api_key")
    if not api_key:
        raise RuntimeError("Tenant LLM configuration missing required OpenAI API key.")

    model_answer = params.get("model_answer") or settings.openai_model_answer
    embed_model = params.get("openai_embed_model") or settings.openai_embed_model
    temperature = params.get("temperature", 0.1)

    Settings.llm = OpenAI(api_key=api_key, model=model_answer, temperature=temperature)
    Settings.embed_model = OpenAIEmbedding(api_key=api_key, model=embed_model)

    return params


@lru_cache(maxsize=1)
def _load_index():
    env_path = (os.getenv("RAG_PERSIST_DIR") or "").strip()
    if env_path:
        persist_dir = Path(env_path).expanduser().resolve()
    else:
        persist_dir = (Path(__file__).parent / "storage" / "vector_store").resolve()
    if not persist_dir.exists():
        raise RuntimeError(
            f"No persisted index found at {persist_dir}. "
            "Run the ingestion CLI to create the vector store."
        )
    storage_context = StorageContext.from_defaults(persist_dir=str(persist_dir))
    return load_index_from_storage(storage_context)


def get_query_engine(tenant: Optional[Dict[str, Any]] = None) -> RetrieverQueryEngine:
    params = _configure_models(tenant)

    top_k = int(params.get("top_k", settings.retriever_candidates))
    rerank_top_n = int(params.get("rerank_top_n", settings.rerank_top_n))
    multi_query = int(params.get("multi_query_count", settings.multi_query_count))
    candidate_pool = max(top_k, int(params.get("retriever_candidates", settings.retriever_candidates)))

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
