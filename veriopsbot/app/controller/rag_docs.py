"""Document management controller functions."""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import List, Sequence

import anyio
from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse


class FolderControllerError(RuntimeError):
    """Base error for folder controller operations."""


def _project_root() -> Path:
    """Return repository root (veriopsbot)."""
    return Path(__file__).resolve().parents[2]


def _resolve_storage_root() -> Path:
    base_dir = _project_root()
    raw_root = os.getenv("RAG_SOURCE_DIR")
    if raw_root:
        candidate = Path(raw_root)
        if not candidate.is_absolute():
            candidate = (base_dir / candidate).resolve()
        else:
            candidate = candidate.resolve()
    else:
        candidate = (base_dir / "app" / "rag_engine" / "storage").resolve()
    candidate.mkdir(parents=True, exist_ok=True)
    return candidate


STORAGE_ROOT: Path = _resolve_storage_root()
_CLIENT_FOLDER_PREFIX = "client"
_SLUG_REGEX = re.compile(r"[^a-z0-9]+")


def tenant_folder_name(tenant_id: int, *, tenant_email: str | None = None) -> str:
    """
    Determine the canonical folder name for a tenant.

    Includes a sanitized version of the tenant's email domain (when available)
    plus the tenant id to guarantee uniqueness.
    """
    domain = ""
    if tenant_email and "@" in tenant_email:
        domain = tenant_email.split("@", 1)[1]
    slug = _SLUG_REGEX.sub("-", domain.lower()).strip("-") if domain else ""
    if slug:
        return f"{_CLIENT_FOLDER_PREFIX}-{slug}-{tenant_id}"
    return f"{_CLIENT_FOLDER_PREFIX}-{tenant_id}"


def _validate_component(name: str, *, label: str) -> str:
    if not name:
        raise ValueError(f"{label} name must not be empty.")
    cleaned = Path(name).name
    if cleaned != name:
        raise ValueError(f"Invalid {label} name '{name}'. Path separators are not allowed.")
    return cleaned


def _folder_path(folder_name: str) -> Path:
    safe_name = _validate_component(folder_name, label="Folder")
    folder = STORAGE_ROOT / safe_name
    return folder


def ensure_folder(folder_name: str) -> Path:
    folder = _folder_path(folder_name)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


async def save_folder_files(folder_name: str, files: Sequence[UploadFile]) -> List[str]:
    if not files:
        raise ValueError("At least one file must be provided.")

    folder = _folder_path(folder_name)
    saved: List[str] = []

    for upload in files:
        filename = upload.filename or ""
        safe_filename = _validate_component(filename, label="File")
        data = await upload.read()
        await anyio.to_thread.run_sync(_write_file_bytes, folder, safe_filename, data)
        await upload.seek(0)
        saved.append(safe_filename)

    return saved


def _write_file_bytes(folder: Path, filename: str, data: bytes) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / filename
    target.write_bytes(data)


def list_folder_files(folder_name: str) -> List[str]:
    folder = _folder_path(folder_name)
    if not folder.exists() or not folder.is_dir():
        raise FileNotFoundError(f"Folder '{folder_name}' was not found.")
    return sorted(p.name for p in folder.iterdir() if p.is_file())


def list_all_folders() -> List[str]:
    if not STORAGE_ROOT.exists() or not STORAGE_ROOT.is_dir():
        return []
    return sorted(path.name for path in STORAGE_ROOT.iterdir() if path.is_dir())


def get_folder_file_path(folder_name: str, file_name: str) -> Path:
    folder = _folder_path(folder_name)
    if not folder.exists() or not folder.is_dir():
        raise FileNotFoundError(f"Folder '{folder_name}' was not found.")

    safe_filename = _validate_component(file_name, label="File")
    target = folder / safe_filename
    if not target.exists() or not target.is_file():
        raise FileNotFoundError(f"File '{safe_filename}' was not found in folder '{folder_name}'.")
    return target


def remove_folder(folder_name: str) -> List[str]:
    folder = _folder_path(folder_name)
    if not folder.exists() or not folder.is_dir():
        raise FileNotFoundError(f"Folder '{folder_name}' was not found.")

    deleted_files: List[str] = [
        path.relative_to(folder).as_posix()
        for path in folder.rglob("*")
        if path.is_file()
    ]

    shutil.rmtree(folder)
    return sorted(deleted_files)


def delete_files(folder_name: str, file_names: Sequence[str]) -> List[str]:
    folder = _folder_path(folder_name)
    if not folder.exists() or not folder.is_dir():
        raise FileNotFoundError(f"Folder '{folder_name}' was not found.")

    deleted: List[str] = []
    for name in file_names:
        if not name:
            continue
        safe_filename = _validate_component(name, label="File")
        target = folder / safe_filename
        if not target.exists() or not target.is_file():
            continue
        target.unlink()
        deleted.append(safe_filename)

    return sorted(deleted)


async def upload_documents(folder_name: str, files: list[UploadFile]):
    try:
        saved = await save_folder_files(folder_name, files)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"folder": folder_name, "files": saved}


def list_documents(folder_name: str):
    try:
        documents = list_folder_files(folder_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Folder not found.") from exc
    return {"folder": folder_name, "files": documents}


def download_document(folder_name: str, file_name: str) -> FileResponse:
    try:
        path = get_folder_file_path(folder_name, file_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="File not found.") from exc
    return FileResponse(path, filename=path.name)


def delete_folder(folder_name: str):
    try:
        deleted = remove_folder(folder_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Folder not found.") from exc
    return {"folder": folder_name, "deleted": deleted}


__all__ = [
    "FolderControllerError",
    "STORAGE_ROOT",
    "tenant_folder_name",
    "ensure_folder",
    "save_folder_files",
    "list_folder_files",
    "list_all_folders",
    "get_folder_file_path",
    "delete_files",
    "remove_folder",
    "upload_documents",
    "list_documents",
    "download_document",
    "delete_folder",
]
