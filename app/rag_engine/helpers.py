from __future__ import annotations
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any
from llama_index.core import Settings, StorageContext, load_index_from_storage
from llama_index.core.postprocessor.llm_rerank import LLMRerank
from llama_index.core.query_engine.retriever_query_engine import RetrieverQueryEngine
from llama_index.core.response_synthesizers import get_response_synthesizer
from llama_index.core.retrievers.fusion_retriever import QueryFusionRetriever
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI

from app.config import settings

DEFAULT_STORAGE_DIR = Path(__file__).parent / "storage"
PERSIST_DIR = settings.resolve_path(
    settings.rag_persist_dir, DEFAULT_STORAGE_DIR / "vector_store"
)


def _llm_kwargs(extra: Dict[str, Any]) -> Dict[str, Any]:
    if settings.openai_api_key:
        extra = {**extra, "api_key": settings.openai_api_key}
    return extra


# Configure LlamaIndex globals once.
Settings.llm = OpenAI(**_llm_kwargs({"model": settings.openai_model_answer, "temperature": 0.1}))
Settings.embed_model = OpenAIEmbedding(**_llm_kwargs({"model": settings.openai_embed_model}))


@lru_cache(maxsize=1)
def get_query_engine():
    if not PERSIST_DIR.exists():
        raise RuntimeError(
            f"No persisted index found at {PERSIST_DIR}. "
            "Run the ingestion CLI to create the vector store."
        )
    storage_context = StorageContext.from_defaults(persist_dir=str(PERSIST_DIR))
    index = load_index_from_storage(storage_context)
    base_retriever = index.as_retriever(
        similarity_top_k=settings.retriever_candidates
    )

    fusion_retriever = QueryFusionRetriever(
        retrievers=[base_retriever],
        llm=Settings.llm,
        similarity_top_k=settings.retriever_candidates,
        num_queries=settings.multi_query_count,
        verbose=False,
    )

    reranker = LLMRerank(llm=Settings.llm, top_n=settings.rerank_top_n)

    response_synthesizer = get_response_synthesizer(
        llm=Settings.llm,
        response_mode="compact",
    )

    return RetrieverQueryEngine(
        retriever=fusion_retriever,
        node_postprocessors=[reranker],
        response_synthesizer=response_synthesizer,
    )
