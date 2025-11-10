from __future__ import annotations

import mimetypes
import secrets
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlencode

import bcrypt
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.controller import rag_docs, rag_ingest
from app.db.repository import (
    create_user,
    get_params_by_tenant_id,
    get_user_by_email,
    invalidate_params_cache,
    invalidate_tenant_params_cache,
    update_crm_settings,
    update_llm_settings,
    update_omnichannel_settings,
)

router = APIRouter()

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)

SESSION_COOKIE_NAME = "session_token"
SESSION_MAX_AGE = 60 * 60 * 8  # 8 hours
SESSION_STORE: dict[str, Dict[str, Any]] = {}

PROVIDER_OPTIONS: list[str] = [
    "openai",
    # "gemini"
    ]
MODEL_OPTIONS: list[str] = [
    "gpt-4o-mini",
    # "gpt-4o",
    # "gpt-4.1-mini",
    # "gpt-3.5-turbo",
    # "claude-3-haiku",
]
HANDOFF_PRIORITIES: list[str] = ["low", "medium", "high", "urgent"]
EMBED_MODEL_OPTIONS: list[str] = [
    "text-embedding-3-small",
    # "text-embedding-3-large",
    # "text-embedding-ada-002",
    # "models/text-embedding-004",
]
CROSS_ENCODER_OPTIONS: list[str] = [
    "cross-encoder/ms-marco-MiniLM-L-6-v2",
    # "cross-encoder/ms-marco-electra-base",
    # "cross-encoder/stsb-roberta-base",
]


def _redirect_documents(**params: str | None) -> RedirectResponse:
    final_params = {key: value for key, value in params.items() if value}
    query = urlencode(final_params)
    url = "/documents"
    if query:
        url = f"{url}?{query}"
    return RedirectResponse(url=url, status_code=status.HTTP_303_SEE_OTHER)


def _get_session(request: Request) -> Dict[str, Any] | None:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None
    return SESSION_STORE.get(token)


def _issue_session_response(
    user: Dict[str, Any],
    *,
    redirect_url: str = "/settings",
) -> RedirectResponse:
    token = secrets.token_urlsafe(32)
    SESSION_STORE[token] = {
        "user_id": user["id"],
        "tenant_id": user["tenant_id"],
        "email": user["email"],
    }
    response = RedirectResponse(
        url=redirect_url,
        status_code=status.HTTP_303_SEE_OTHER,
    )
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
    )
    return response


def _client_folder_name(session: Dict[str, Any]) -> str:
    return rag_docs.tenant_folder_name(
        tenant_id=session["tenant_id"],
        tenant_email=session.get("email"),
    )


def _file_type_label(file_name: str) -> str:
    mime, _ = mimetypes.guess_type(file_name)
    if mime:
        _, _, subtype = mime.partition("/")
        if subtype:
            return subtype.replace("-", " ").upper()
        return mime.upper()
    suffix = Path(file_name).suffix.lstrip(".")
    if suffix:
        return suffix.upper()
    return "Unknown"


def _build_file_rows(folder_name: str, file_names: list[str]) -> list[Dict[str, str]]:
    rows: list[Dict[str, str]] = []
    for file_name in file_names:
        rows.append(
            {
                "name": file_name,
                "type": _file_type_label(file_name),
                "url": f"/rag/docs/{folder_name}/{file_name}",
            }
        )
    return rows


def _build_form_values(
    config: Dict[str, Any],
    overrides: Dict[str, str] | None = None,
) -> Dict[str, str]:
    overrides = overrides or {}
    llm_params = config.get("llm_params") or {}
    crm_params = config.get("crm_params") or {}
    omni_params = config.get("omnichannel") or {}

    def pick(key: str, default: Any = "") -> str:
        if overrides is not None and key in overrides:
            value = overrides[key]
        else:
            value = default
        return "" if value is None else str(value)

    return {
        "llm_name": pick("llm_name", llm_params.get("name")),
        "llm_api_key": pick("llm_api_key", llm_params.get("api_key")),
        "llm_model_answer": pick("llm_model_answer", llm_params.get("model_answer")),
        "llm_top_k": pick("llm_top_k", llm_params.get("top_k")),
        "llm_temperature": pick("llm_temperature", llm_params.get("temperature")),
        "llm_handoff_priority": pick(
            "llm_handoff_priority",
            llm_params.get("handoff_priority"),
        ),
        "llm_openai_embed_model": pick(
            "llm_openai_embed_model",
            llm_params.get("openai_embed_model"),
        ),
        "llm_handoff_private_note": pick(
            "llm_handoff_private_note",
            llm_params.get("handoff_private_note"),
        ),
        "llm_handoff_public_reply": pick(
            "llm_handoff_public_reply",
            llm_params.get("handoff_public_reply"),
        ),
        "llm_rag_cross_encoder_model": pick(
            "llm_rag_cross_encoder_model",
            llm_params.get("rag_cross_encoder_model"),
        ),
        "llm_monthly_limit": pick(
            "llm_monthly_limit",
            llm_params.get("monthly_llm_request_limit"),
        ),
        "crm_url": pick("crm_url", crm_params.get("url")),
        "crm_token": pick("crm_token", crm_params.get("token")),
        "chatwoot_api_url": pick(
            "chatwoot_api_url",
            omni_params.get("chatwoot_api_url"),
        ),
        "chatwoot_account_id": pick(
            "chatwoot_account_id",
            omni_params.get("chatwoot_account_id"),
        ),
        "chatwoot_api_access_token": pick(
            "chatwoot_api_access_token",
            omni_params.get("chatwoot_api_access_token"),
        ),
        "chatwoot_bot_access_token": pick(
            "chatwoot_bot_access_token",
            omni_params.get("chatwoot_bot_access_token"),
        ),
    }


@router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    session = _get_session(request)
    target = "/settings" if session else "/login"
    return RedirectResponse(url=target, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    session = _get_session(request)
    if session:
        return RedirectResponse(url="/settings", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "error": None,
            "email": "",
        },
    )


@router.post("/login", response_class=HTMLResponse)
async def login(request: Request):
    form = await request.form()
    email_raw = (form.get("email") or "").strip()
    password = form.get("password") or ""
    email = email_raw.lower()

    if not email or not password:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Email and password are required.",
                "email": email_raw,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    user = await get_user_by_email(email)
    password_hash = user.get("password_hash") if user else None

    if not user or not password_hash:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Invalid email or password.",
                "email": email_raw,
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    if not bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8")):
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Invalid email or password.",
                "email": email_raw,
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    return _issue_session_response(user)


@router.get("/register", response_class=HTMLResponse)
async def register_form(request: Request):
    session = _get_session(request)
    if session:
        return RedirectResponse(url="/settings", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        "register.html",
        {
            "request": request,
            "errors": [],
            "email": "",
            "tenant_id": "",
        },
    )


@router.post("/register", response_class=HTMLResponse)
async def register(request: Request):
    session = _get_session(request)
    if session:
        return RedirectResponse(url="/settings", status_code=status.HTTP_303_SEE_OTHER)

    form = await request.form()
    email_raw = (form.get("email") or "").strip()
    email = email_raw.lower()
    password = form.get("password") or ""
    confirm_password = form.get("confirm_password") or ""
    tenant_id_raw = (form.get("tenant_id") or "").strip()

    errors: list[str] = []
    tenant_id: int | None = None

    if not tenant_id_raw:
        errors.append("Tenant ID is required.")
    else:
        try:
            tenant_id = int(tenant_id_raw)
        except ValueError:
            errors.append("Tenant ID must be a number.")

    if not email:
        errors.append("Email is required.")
    if not password:
        errors.append("Password is required.")
    if password and len(password) < 8:
        errors.append("Password must be at least 8 characters long.")
    if password != confirm_password:
        errors.append("Passwords do not match.")

    existing_user = await get_user_by_email(email) if email else {}
    if existing_user:
        errors.append("An account with this email already exists.")

    if errors:
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "errors": errors,
                "email": email_raw,
                "tenant_id": tenant_id_raw,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode(
        "utf-8"
    )

    try:
        assert tenant_id is not None
        user = await create_user(
            tenant_id=tenant_id,
            email=email,
            password_hash=password_hash,
        )
    except Exception:
        errors.append("Failed to create user. Please try again or contact support.")
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "errors": errors,
                "email": email_raw,
                "tenant_id": tenant_id_raw,
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return _issue_session_response(user)


@router.get("/logout")
async def logout(request: Request):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        SESSION_STORE.pop(token, None)

    response = RedirectResponse(
        url="/login",
        status_code=status.HTTP_303_SEE_OTHER,
    )
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    session = _get_session(request)
    if not session:
        return RedirectResponse(
            url="/login",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    config = await get_params_by_tenant_id(session["tenant_id"])
    form_values = _build_form_values(config)
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "user_email": session["email"],
            "form_values": form_values,
            "message": None,
            "errors": [],
            "provider_options": PROVIDER_OPTIONS,
            "model_options": MODEL_OPTIONS,
            "handoff_priorities": HANDOFF_PRIORITIES,
            "embed_options": EMBED_MODEL_OPTIONS,
            "cross_encoder_options": CROSS_ENCODER_OPTIONS,
        },
    )


@router.post("/settings", response_class=HTMLResponse)
async def update_settings(request: Request):
    session = _get_session(request)
    if not session:
        return RedirectResponse(
            url="/login",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    config = await get_params_by_tenant_id(session["tenant_id"])
    form = await request.form()
    form_dict: Dict[str, str] = {
        key: (value.strip() if isinstance(value, str) else value)
        for key, value in form.items()
    }

    form_values = _build_form_values(config, overrides=form_dict)
    errors: list[str] = []

    if not config:
        errors.append("Tenant configuration not found. Please contact support.")

    required_fields = {
        "llm_name": "LLM name",
        "llm_api_key": "LLM API key",
        "llm_model_answer": "LLM model answer",
        "crm_url": "CRM URL",
        "crm_token": "CRM token",
        "chatwoot_api_url": "Chatwoot API URL",
        "chatwoot_account_id": "Chatwoot account ID",
        "chatwoot_api_access_token": "Chatwoot API access token",
        "chatwoot_bot_access_token": "Chatwoot bot access token",
    }
    for field, label in required_fields.items():
        if not form_dict.get(field):
            errors.append(f"{label} is required.")

    current_llm = config.get("llm_params") or {}
    current_crm = config.get("crm_params") or {}
    current_omni = config.get("omnichannel") or {}

    top_k_raw = form_dict.get("llm_top_k", "")
    top_k = current_llm.get("top_k")
    if top_k_raw:
        try:
            top_k = int(top_k_raw)
        except ValueError:
            errors.append("LLM Top K must be an integer.")

    temperature_raw = form_dict.get("llm_temperature", "")
    temperature = current_llm.get("temperature")
    if temperature_raw:
        try:
            temperature = float(temperature_raw)
        except ValueError:
            errors.append("LLM temperature must be a number.")

    monthly_limit_raw = form_dict.get("llm_monthly_limit", "")
    monthly_limit = current_llm.get("monthly_llm_request_limit")
    if monthly_limit_raw == "":
        monthly_limit = None
    elif monthly_limit_raw:
        try:
            monthly_limit = int(monthly_limit_raw)
        except ValueError:
            errors.append("Monthly LLM request limit must be an integer.")

    llm_id = config.get("llm_id")
    crm_id = config.get("crm_id")
    omnichannel_id = config.get("omnichannel_id")
    if not llm_id:
        errors.append("LLM settings are missing for this tenant.")
    if not crm_id:
        errors.append("CRM settings are missing for this tenant.")
    if not omnichannel_id:
        errors.append("Omnichannel settings are missing for this tenant.")

    if errors:
        return templates.TemplateResponse(
            "settings.html",
            {
                "request": request,
                "user_email": session["email"],
                "form_values": form_values,
                "message": None,
                "errors": errors,
                "provider_options": PROVIDER_OPTIONS,
                "model_options": MODEL_OPTIONS,
                "handoff_priorities": HANDOFF_PRIORITIES,
                "embed_options": EMBED_MODEL_OPTIONS,
                "cross_encoder_options": CROSS_ENCODER_OPTIONS,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    updated_llm_params = dict(current_llm)
    updated_llm_params["name"] = form_dict["llm_name"]
    updated_llm_params["api_key"] = form_dict["llm_api_key"]
    updated_llm_params["model_answer"] = form_dict["llm_model_answer"]

    def set_or_pop(mapping: Dict[str, Any], key: str, value: Any) -> None:
        if value is None:
            mapping.pop(key, None)
        elif isinstance(value, str) and value == "":
            mapping.pop(key, None)
        else:
            mapping[key] = value

    set_or_pop(
        updated_llm_params,
        "handoff_priority",
        form_dict.get("llm_handoff_priority"),
    )
    set_or_pop(
        updated_llm_params,
        "openai_embed_model",
        form_dict.get("llm_openai_embed_model"),
    )
    set_or_pop(
        updated_llm_params,
        "handoff_private_note",
        form_dict.get("llm_handoff_private_note"),
    )
    set_or_pop(
        updated_llm_params,
        "handoff_public_reply",
        form_dict.get("llm_handoff_public_reply"),
    )
    set_or_pop(
        updated_llm_params,
        "rag_cross_encoder_model",
        form_dict.get("llm_rag_cross_encoder_model"),
    )

    if top_k is None:
        updated_llm_params.pop("top_k", None)
    else:
        updated_llm_params["top_k"] = top_k

    if temperature is None:
        updated_llm_params.pop("temperature", None)
    else:
        updated_llm_params["temperature"] = temperature

    if monthly_limit is None:
        updated_llm_params.pop("monthly_llm_request_limit", None)
    else:
        updated_llm_params["monthly_llm_request_limit"] = monthly_limit

    updated_crm_params = dict(current_crm)
    updated_crm_params["url"] = form_dict["crm_url"]
    updated_crm_params["token"] = form_dict["crm_token"]

    updated_omni_params = dict(current_omni)
    updated_omni_params["chatwoot_api_url"] = form_dict["chatwoot_api_url"]
    updated_omni_params["chatwoot_account_id"] = form_dict["chatwoot_account_id"]
    updated_omni_params["chatwoot_api_access_token"] = form_dict[
        "chatwoot_api_access_token"
    ]
    updated_omni_params["chatwoot_bot_access_token"] = form_dict[
        "chatwoot_bot_access_token"
    ]

    await update_llm_settings(
        llm_id=llm_id,
        params=updated_llm_params,
    )
    await update_crm_settings(
        crm_id=crm_id,
        params=updated_crm_params,
    )
    await update_omnichannel_settings(
        omnichannel_id=omnichannel_id,
        params=updated_omni_params,
    )

    await invalidate_params_cache(omnichannel_id)
    await invalidate_tenant_params_cache(session["tenant_id"])

    refreshed_config = await get_params_by_tenant_id(session["tenant_id"])
    refreshed_form_values = _build_form_values(refreshed_config)

    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "user_email": session["email"],
            "form_values": refreshed_form_values,
            "message": "Settings updated successfully.",
            "errors": [],
            "provider_options": PROVIDER_OPTIONS,
            "model_options": MODEL_OPTIONS,
            "handoff_priorities": HANDOFF_PRIORITIES,
            "embed_options": EMBED_MODEL_OPTIONS,
            "cross_encoder_options": CROSS_ENCODER_OPTIONS,
        },
    )


@router.get("/documents", response_class=HTMLResponse)
async def documents_page(request: Request):
    session = _get_session(request)
    if not session:
        return RedirectResponse(
            url="/login",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    client_folder = _client_folder_name(session)
    rag_docs.ensure_folder(client_folder)
    try:
        client_files = rag_docs.list_folder_files(client_folder)
    except FileNotFoundError:
        client_files = []

    file_rows = _build_file_rows(client_folder, client_files)

    message = request.query_params.get("message")
    error_param = request.query_params.get("error")
    errors = [error_param] if error_param else []

    return templates.TemplateResponse(
        "documents.html",
        {
            "request": request,
            "user_email": session["email"],
            "client_folder": client_folder,
            "file_rows": file_rows,
            "message": message,
            "errors": errors,
        },
    )


@router.post("/documents/upload")
async def documents_upload(
    request: Request,
    files: list[UploadFile] = File(...),
):
    session = _get_session(request)
    if not session:
        return RedirectResponse(
            url="/login",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    folder_name = _client_folder_name(session)

    if not files or all((file.filename or "").strip() == "" for file in files):
        return _redirect_documents(
            error="Please select at least one file to upload.",
        )

    try:
        result = await rag_docs.upload_documents(folder_name, files)
    except HTTPException as exc:
        detail = str(exc.detail) if exc.detail else "Failed to upload documents."
        return _redirect_documents(error=detail)
    except ValueError as exc:
        return _redirect_documents(error=str(exc))

    uploaded = result.get("files", [])
    message = f"Uploaded {len(uploaded)} file(s) to '{folder_name}'."
    return _redirect_documents(message=message)


@router.post("/documents/files/delete")
async def documents_delete_files(
    request: Request,
    selected_files: list[str] = Form([]),
):
    session = _get_session(request)
    if not session:
        return RedirectResponse(
            url="/login",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    if not selected_files:
        return _redirect_documents(error="Select at least one file to delete.")

    folder_name = _client_folder_name(session)

    try:
        deleted = rag_docs.delete_files(folder_name, selected_files)
    except FileNotFoundError:
        return _redirect_documents(error="Client folder not found.")
    except ValueError as exc:
        return _redirect_documents(error=str(exc))

    if not deleted:
        return _redirect_documents(error="No matching files found to delete.")

    message = f"Deleted {len(deleted)} file(s) from '{folder_name}'."
    return _redirect_documents(message=message)


@router.post("/documents/ingest")
async def documents_ingest(request: Request):
    session = _get_session(request)
    if not session:
        return RedirectResponse(
            url="/login",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    folder = _client_folder_name(session)

    payload = rag_ingest.IngestRequest(
        folder=folder,
        tenant_id=session["tenant_id"],
    )

    try:
        result = await rag_ingest.trigger_ingest(payload)
    except HTTPException as exc:
        detail = str(exc.detail) if exc.detail else "Failed to ingest documents."
        return _redirect_documents(error=detail)
    except Exception as exc:  # pragma: no cover - defensive
        return _redirect_documents(error=str(exc))

    ingested = result.get("documents_ingested")
    message = (
        f"Number of ingested documents: {ingested}"
    )
    return _redirect_documents(message=message)


__all__ = ["router"]
