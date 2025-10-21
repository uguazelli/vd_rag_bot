from __future__ import annotations
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

class SettingsError(ValueError):
    """Raised when environment configuration is invalid."""


class AppSettings:
    """Project-wide environment configuration loaded once at import time."""

    def __init__(self) -> None:

        self.openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
        self.openai_model_answer: str = os.getenv(
            "OPENAI_MODEL_ANSWER", "gpt-4o-mini"
        )
        self.openai_embed_model: str = os.getenv(
            "OPENAI_EMBED_MODEL", "text-embedding-3-small"
        )

        self.top_k: int = self._read_int("TOP_K", default=4, minimum=1)
        self.multi_query_count: int = self._read_int(
            "MULTI_QUERY_COUNT", default=3, minimum=1
        )

        raw_rerank = os.getenv("RERANK_TOP_N")
        self._rerank_top_n: Optional[int] = (
            self._read_int("RERANK_TOP_N", minimum=1)
            if raw_rerank is not None and raw_rerank.strip()
            else None
        )

        raw_candidates = os.getenv("RETRIEVER_CANDIDATES")
        self._retriever_candidates: Optional[int] = (
            self._read_int("RETRIEVER_CANDIDATES", minimum=1)
            if raw_candidates is not None and raw_candidates.strip()
            else None
        )

        self.rag_persist_dir: Optional[str] = os.getenv("RAG_PERSIST_DIR")
        self.rag_source_dir: Optional[str] = os.getenv("RAG_SOURCE_DIR")

        self.twenty_api_key: Optional[str] = os.getenv("TWENTY_API_KEY")
        self.twenty_base_url: str = os.getenv(
            "TWENTY_BASE_URL", "http://localhost:8000"
        )

    @staticmethod
    def _read_int(
        env_name: str, *, default: Optional[int] = None, minimum: Optional[int] = None
    ) -> int:
        raw = os.getenv(env_name)
        if raw is None or not raw.strip():
            if default is None:
                raise SettingsError(
                    f"Environment variable {env_name} is required but not set."
                )
            value = default
        else:
            try:
                value = int(raw)
            except ValueError as exc:
                raise SettingsError(
                    f"Environment variable {env_name} must be an integer, got {raw!r}"
                ) from exc

        if minimum is not None and value < minimum:
            raise SettingsError(
                f"Environment variable {env_name} must be >= {minimum}, got {value}"
            )
        return value

    @property
    def rerank_top_n(self) -> int:
        """Return the effective rerank depth."""
        base = self._rerank_top_n if self._rerank_top_n is not None else max(5, self.top_k)
        return max(base, 1)

    @property
    def retriever_candidates(self) -> int:
        """Return the candidate pool size used for retrieval prior to reranking."""
        base = (
            self._retriever_candidates
            if self._retriever_candidates is not None
            else max(10, self.rerank_top_n * 2)
        )
        return max(base, self.rerank_top_n)

    @staticmethod
    def resolve_path(value: Optional[str], default: Path) -> Path:
        """Convert optional string paths into resolved Path instances."""
        if value and value.strip():
            return Path(value).expanduser().resolve()
        return default.resolve()


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return AppSettings()


settings = get_settings()
