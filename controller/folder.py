"""Folder-level document management utilities."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import List, Sequence

import anyio
from fastapi import UploadFile


class FolderControllerError(RuntimeError):
    """Base error for folder controller operations."""


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


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
        # Reset stream so FastAPI can handle cleanup correctly.
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


__all__ = [
    "FolderControllerError",
    "STORAGE_ROOT",
    "save_folder_files",
    "list_folder_files",
    "get_folder_file_path",
    "remove_folder",
]
