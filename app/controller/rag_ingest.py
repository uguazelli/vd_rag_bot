"""RAG ingestion controller functions."""

from pydantic import BaseModel
from fastapi import HTTPException

from app.rag_engine.ingest import ingest_documents, IngestError


class IngestRequest(BaseModel):
    folder: str
    tenant_id: int
    provider: str | None = None
    embed_model: str | None = None


async def trigger_ingest(payload: IngestRequest):
    try:
        ingested, resolved_provider, resolved_model = await ingest_documents(
            tenant_id=payload.tenant_id,
            folder_name=payload.folder,
            provider=payload.provider,
            embed_model=payload.embed_model,
        )
    except IngestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "tenant_id": payload.tenant_id,
        "folder": payload.folder,
        "provider": resolved_provider,
        "embed_model": resolved_model,
        "documents_ingested": ingested,
    }


__all__ = ["IngestRequest", "trigger_ingest"]
