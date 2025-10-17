from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from llama_index.core import (
    Settings,
    StorageContext,
    load_index_from_storage,
)
from llama_index.core.postprocessor.llm_rerank import LLMRerank
from llama_index.core.query_engine.retriever_query_engine import RetrieverQueryEngine
from llama_index.core.response_synthesizers import get_response_synthesizer
from llama_index.core.retrievers.fusion_retriever import QueryFusionRetriever
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANSWER_MODEL = os.getenv("OPENAI_MODEL_ANSWER", "gpt-4o-mini")
EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
TOP_K = int(os.getenv("TOP_K", "4"))
MULTI_QUERY_COUNT = int(os.getenv("MULTI_QUERY_COUNT", "3"))
RERANK_TOP_N = int(os.getenv("RERANK_TOP_N", str(max(5, TOP_K))))
RETRIEVER_CANDIDATES = max(
    int(os.getenv("RETRIEVER_CANDIDATES", str(max(10, RERANK_TOP_N * 2)))),
    RERANK_TOP_N,
)

DEFAULT_STORAGE_DIR = Path(__file__).parent / "storage"
PERSIST_DIR = Path(
    os.getenv(
        "RAG_PERSIST_DIR",
        str((DEFAULT_STORAGE_DIR / "vector_store").resolve()),
    )
)

# Configure LlamaIndex globals once.
Settings.llm = OpenAI(model=ANSWER_MODEL, temperature=0.1)
Settings.embed_model = OpenAIEmbedding(model=EMBED_MODEL)


@lru_cache(maxsize=1)
def get_query_engine():
    if not PERSIST_DIR.exists():
        raise RuntimeError(
            f"No persisted index found at {PERSIST_DIR}. "
            "Run the ingestion CLI to create the vector store."
        )
    storage_context = StorageContext.from_defaults(persist_dir=str(PERSIST_DIR))
    index = load_index_from_storage(storage_context)
    base_retriever = index.as_retriever(similarity_top_k=RETRIEVER_CANDIDATES)

    fusion_retriever = QueryFusionRetriever(
        retrievers=[base_retriever],
        llm=Settings.llm,
        similarity_top_k=RETRIEVER_CANDIDATES,
        num_queries=MULTI_QUERY_COUNT,
        verbose=False,
    )

    reranker = LLMRerank(llm=Settings.llm, top_n=RERANK_TOP_N)

    response_synthesizer = get_response_synthesizer(
        llm=Settings.llm,
        response_mode="compact",
    )

    return RetrieverQueryEngine(
        retriever=fusion_retriever,
        node_postprocessors=[reranker],
        response_synthesizer=response_synthesizer,
    )
