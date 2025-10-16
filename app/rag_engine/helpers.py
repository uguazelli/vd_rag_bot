from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import List

from llama_index.core import Settings, SimpleDirectoryReader, VectorStoreIndex
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANSWER_MODEL = os.getenv("OPENAI_MODEL_ANSWER", "gpt-4o-mini")
EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
TOP_K = int(os.getenv("TOP_K", "4"))

KB_PATH = Path( os.getenv("KNOWLEDGE_FILE", str((Path(__file__).parent / "kb.txt").resolve()),))

# Configure LlamaIndex globals once.
Settings.llm = OpenAI(model=ANSWER_MODEL, temperature=0.1)
Settings.embed_model = OpenAIEmbedding(model=EMBED_MODEL)

def _load_documents() -> List:
    if not KB_PATH.exists():
        return []
    if KB_PATH.is_dir():
        reader = SimpleDirectoryReader(str(KB_PATH))
    else:
        reader = SimpleDirectoryReader(input_files=[str(KB_PATH)])
    return reader.load_data()


@lru_cache(maxsize=1)
def get_query_engine():
    documents = _load_documents()
    if not documents:
        raise RuntimeError(f"No knowledge base documents found at {KB_PATH}")
    index = VectorStoreIndex.from_documents(documents)
    return index.as_query_engine(similarity_top_k=TOP_K)
