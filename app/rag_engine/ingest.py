from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

from llama_index.core import SimpleDirectoryReader, StorageContext, VectorStoreIndex

from .helpers import DEFAULT_STORAGE_DIR, PERSIST_DIR

DOCUMENTS_DIR = Path(
    os.getenv(
        "RAG_SOURCE_DIR",
        str(DEFAULT_STORAGE_DIR.resolve()),
    )
)


def rebuild_index(documents_dir: Path, persist_dir: Path) -> int:
    if not documents_dir.exists():
        raise FileNotFoundError(
            f"Document directory not found: {documents_dir}. "
            "Place your files there before running the ingest command."
        )

    reader = SimpleDirectoryReader(str(documents_dir))
    documents = reader.load_data()
    if not documents:
        raise RuntimeError(
            f"No documents found in {documents_dir}. "
            "Add files to ingest before running the command."
        )

    if persist_dir.exists():
        shutil.rmtree(persist_dir)
    persist_dir.mkdir(parents=True, exist_ok=True)

    storage_context = StorageContext.from_defaults()
    index = VectorStoreIndex.from_documents(documents, storage_context=storage_context)
    index.storage_context.persist(persist_dir=str(persist_dir))
    return len(documents)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Builds the vector store from all files located in app/rag_engine/storage."
        )
    )
    parser.add_argument(
        "--input-dir",
        default=str(DOCUMENTS_DIR),
        help="Path to the folder containing knowledge source files (default: app/rag_engine/storage).",
    )
    parser.add_argument(
        "--persist-dir",
        default=str(PERSIST_DIR),
        help="Path where the vector index should be stored (default: app/rag_engine/storage/vector_store).",
    )
    args = parser.parse_args()

    documents_dir = Path(args.input_dir).expanduser().resolve()
    persist_dir = Path(args.persist_dir).expanduser().resolve()

    count = rebuild_index(documents_dir=documents_dir, persist_dir=persist_dir)
    print(f"Ingested {count} documents into {persist_dir}")


if __name__ == "__main__":
    main()
