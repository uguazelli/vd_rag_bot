from fastapi import FastAPI, Request
from app.chatwoot.handoff import perform_handoff, send_message
from app.db.repository import get_params_by_omnichannel_id
from app.rag_engine.rag import initial_state, handle_input
import os
import httpx
import requests


app = FastAPI()
SESSIONS = {}

# Defaults are cheap/solid; override via env if you want
CHATWOOT_BOT_ACCESS_TOKEN = os.getenv("CHATWOOT_BOT_ACCESS_TOKEN")
CHATWOOT_API_URL = os.getenv("CHATWOOT_API_URL")
HANDOFF_PUBLIC_REPLY = os.getenv("HANDOFF_PUBLIC_REPLY")
HANDOFF_PRIVATE_NOTE = os.getenv("HANDOFF_PRIVATE_NOTE")
HANDOFF_PRIORITY = os.getenv("HANDOFF_PRIORITY")
HTTP_TIMEOUT = 10.0


@app.get("/health")
async def health():
    print("🤖 Health check", flush=True)
    return {"message": "Status OK"}

@app.post("/chatwoot/webhook")
async def webhook(request: Request):
    payload = await request.json()
    print("☎️ Chatwoot webhook payload received:", payload)

    if not payload.get("event").startswith("contact_"):
        return {"message": "Not a contact event"}
    if not payload.get("phone_number") and not payload.get("email"):
        return {"message": "No phone number or email detected"}

    n8n = requests.post("http://host.docker.internal:5678/webhook/chatwoot", json=payload).json()
    n8ntest = requests.post("http://host.docker.internal:5678/webhook-test/chatwoot", json=payload).json()
    print("🔄 N8N webhook:", n8n)
    print("🔄 N8N test webhook:", n8ntest)
    return {"message": "Chatwoot webhook processed"}


@app.post("/twenty/webhook")
async def twenty_webhook(request: Request):
    payload = await request.json()
    print("👩‍🔧 Twenty webhook:", payload)

    if payload.get("record", {}).get("deletedAt"):
        print("🧹 Deletion detected, skipping n8n call.")
        return {"message": "Deletion detected, skipping n8n call."}

    n8n = requests.post("http://host.docker.internal:5678/webhook/twenty", json=payload).json()
    n8ntest = requests.post("http://host.docker.internal:5678/webhook-test/twenty", json=payload).json()
    print("🔄 N8N webhook:", n8n)
    print("🔄 N8N test webhook:", n8ntest)
    return {"message": "Twenty webhook processed"}


@app.post("/bot")
async def bot(request: Request):

    data = await request.json()
    convo = data.get("conversation", {}) or {}
    assignee_id = (convo.get("meta", {}) or {}).get("assignee", {}) or {}
    assignee_id = assignee_id.get("id")
    # print("🤖 VD Bot webhook:", data)

    # Ignore conversations assigned to someone
    if assignee_id:
        return {"message": "Conversation is assigned to someone"}

    # Must be a message creation event.
    if data.get("event") != "message_created":
        return {"message": "Not a message creation event"}

    # MUST be 'incoming' (from user). This reliably prevents the infinite loop.
    if data.get("message_type") != "incoming":
        return {"message": "Not an incoming message"}

    # Ensure a sender exists to prevent KeyError later
    if "sender" not in data:
        return {"message": "No sender detected"}

    account_id = int(data["account"]["id"])
    conversation_id = data["conversation"]["id"]
    user_id = str(data["sender"]["id"])
    text = data.get("content", "") or ""

    # print("🤖 Account ID:", account_id)
    # client_params = await get_params_by_omnichannel_id(account_id)
    # print("🤖 Omnichannel ID:", client_params)

    state = SESSIONS.get(user_id) or initial_state()
    state, reply, status = await handle_input(state, text, account_id)
    SESSIONS[user_id] = state

    # print("🤖 Bot reply:", reply)
    # print("🤖 Bot status:", status)
    # print("🤖 Bot state:", state)


    # Post reply once (Chatwoot will emit an 'outgoing' webhook; we ignore it above)
    async with httpx.AsyncClient() as client:
        if reply == "human_agent":
            # print("😎 Routing to human agent")
            await perform_handoff(
                client=client,
                account_id=account_id,
                conversation_id=conversation_id,
                api_url=CHATWOOT_API_URL,
                access_token=CHATWOOT_BOT_ACCESS_TOKEN,
                public_reply=HANDOFF_PUBLIC_REPLY,
                private_note=HANDOFF_PRIVATE_NOTE,
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

    return {"message": "VD Bot processed"}
