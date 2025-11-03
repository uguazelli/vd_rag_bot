"""Chatwoot bot controller logic."""

from datetime import date
import os

import httpx

from app.chatwoot.handoff import perform_handoff, send_message
from app.db.repository import (
    get_bot_request_total,
    get_params_by_omnichannel_id,
    increment_bot_request_count,
)
from app.rag_engine.rag import handle_input, initial_state


SESSIONS: dict[str, dict] = {}
HANDOFF_PRIORITY = "high"
CHATWOOT_BOT_ACCESS_TOKEN = os.getenv("CHATWOOT_BOT_ACCESS_TOKEN")
CHATWOOT_API_URL = os.getenv("CHATWOOT_API_URL")


async def process_bot_request(data: dict):
    convo = data.get("conversation", {}) or {}
    assignee_id = (convo.get("meta", {}) or {}).get("assignee", {}) or {}
    assignee_id = assignee_id.get("id")

    if assignee_id:
        print("🤖 Conversation is assigned to someone")
        return {"message": "Conversation is assigned to someone"}

    if data.get("event") != "message_created":
        print("🤖 Not a message creation event")
        return {"message": "Not a message creation event"}

    if data.get("message_type") != "incoming":
        print("🤖 Not an incoming message")
        return {"message": "Not an incoming message"}

    if "sender" not in data:
        print("🤖 No sender detected")
        return {"message": "No sender detected"}

    account_id = int(data["account"]["id"])
    conversation_id = data["conversation"]["id"]
    user_id = str(data["sender"]["id"])
    text = data.get("content", "") or ""

    print("🤖 Account ID:", account_id)
    cfg = await get_params_by_omnichannel_id(account_id)
    if not cfg:
        print("🤖 No tenant configuration found for omnichannel id", account_id)
        return {"message": "No tenant configuration found for omnichannel id"}

    tenant_id = int(cfg.get("id", account_id))
    llm_params = cfg.get("llm_params") or {}
    bot_usage_today = None
    bot_usage_month = None
    monthly_usage = None
    monthly_limit = None
    monthly_limit_raw = llm_params.get("monthly_llm_request_limit")

    if monthly_limit_raw is not None:
        try:
            monthly_limit = int(monthly_limit_raw)
        except (TypeError, ValueError):
            monthly_limit = None
            print(
                f"⚠️ Invalid monthly limit configured for tenant {tenant_id}: "
                f"{monthly_limit_raw}"
            )

    if monthly_limit is not None and monthly_limit > 0:
        today = date.today()
        start_of_month = today.replace(day=1)
        try:
            monthly_usage = await get_bot_request_total(tenant_id, start_of_month, today)
            bot_usage_month = monthly_usage
            print(
                f"📊 Bot usage this month for tenant {tenant_id}: "
                f"{monthly_usage}/{monthly_limit}"
            )
        except Exception as exc:
            monthly_usage = None
            bot_usage_month = None
            print(f"⚠️ Failed to fetch monthly usage for tenant {tenant_id}: {exc}")
        else:
            if monthly_usage >= monthly_limit:
                limit_message = llm_params.get(
                    "monthly_llm_limit_reached_reply",
                    "We have reached the automated response limit for this month. "
                    "A human teammate will take it from here.",
                )
                async with httpx.AsyncClient() as client:
                    await send_message(
                        client=client,
                        api_url=CHATWOOT_API_URL,
                        access_token=CHATWOOT_BOT_ACCESS_TOKEN,
                        account_id=account_id,
                        conversation_id=conversation_id,
                        content=limit_message,
                        private=False,
                    )
                return {
                    "message": "Monthly limit reached",
                    "bot_requests_month": monthly_usage,
                    "monthly_limit": monthly_limit,
                }

    try:
        bot_usage_today = await increment_bot_request_count(tenant_id)
        print(f"📈 Bot usage for tenant {tenant_id} today: {bot_usage_today}")
        if bot_usage_month is not None:
            bot_usage_month = bot_usage_month + 1
    except Exception as exc:
        print(f"⚠️ Failed to record bot usage for tenant {tenant_id}: {exc}")

    handoff_public_reply = llm_params.get(
        "handoff_public_reply",
        "Ok, please hold on while I connect you with a human agent.",
    )
    handoff_private_note = llm_params.get(
        "handoff_private_note",
        "Bot routed the conversation for human follow-up.",
    )

    state = SESSIONS.get(user_id) or initial_state()
    print("🤖 Handling the input ...")
    state, reply, status = await handle_input(
        state,
        text,
        tenant_id=cfg.get("id", account_id),
        runtime_config=cfg,
    )
    SESSIONS[user_id] = state

    async with httpx.AsyncClient() as client:
        if reply == "human_agent":
            await perform_handoff(
                client=client,
                account_id=account_id,
                conversation_id=conversation_id,
                api_url=CHATWOOT_API_URL,
                access_token=CHATWOOT_BOT_ACCESS_TOKEN,
                public_reply=handoff_public_reply,
                private_note=handoff_private_note,
                priority=HANDOFF_PRIORITY,
            )
            return {"message": "Routing to human agent"}

        await send_message(
            client=client,
            api_url=CHATWOOT_API_URL,
            access_token=CHATWOOT_BOT_ACCESS_TOKEN,
            account_id=account_id,
            conversation_id=conversation_id,
            content=reply,
            private=False,
        )

    response = {"message": "VD Bot processed"}
    if bot_usage_today is not None:
        response["bot_requests_today"] = bot_usage_today
    if bot_usage_month is not None:
        response["bot_requests_month"] = bot_usage_month
    if monthly_limit is not None:
        response["monthly_limit"] = monthly_limit
    return response


__all__ = ["process_bot_request"]
