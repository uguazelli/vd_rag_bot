from fastapi import FastAPI, Request
from app.chatwoot.handleContactUpdated import handleContactCreated
from app.chatwoot.handoff import perform_handoff, send_message
from app.config import settings
from app.rag_engine.rag import initial_state, handle_input
import httpx

app = FastAPI()
SESSIONS = {}

# Defaults are cheap/solid; override via env if you want
CHATWOOT_BOT_ACCESS_TOKEN = settings.chatwoot_bot_access_token
CHATWOOT_API_URL = settings.chatwoot_api_url
HANDOFF_PUBLIC_REPLY = settings.handoff_public_reply
HANDOFF_PRIVATE_NOTE = settings.handoff_private_note
HANDOFF_PRIORITY = settings.handoff_priority
HTTP_TIMEOUT = 10.0

@app.get("/health")
async def health():
    print("🤖 Health check", flush=True)
    return {"status": "True"}

@app.post("/chatwoot/webhook")
async def webhook(request: Request):
    data = await request.json()
    # print("🤖 Webhook:", data)
    handleContactCreated(data)
    return {"status": "ok"}


@app.post("/twenty/webhook")
async def twenty_webhook(request: Request):
    payload = await request.json()
    print("🔄 Twenty webhook payload received:", payload)

    record = payload.get("record") or {}
    chatwoot_id = record.get("chatwootId")
    if not chatwoot_id:
        return {"status": "ignored"}

    name = record.get("name") or {}
    full_name = f"{name.get('firstName', '')} {name.get('lastName', '')}".strip()
    phone_info = record.get("phones") or {}
    phone = phone_info.get("primaryPhoneNumber")
    calling_code = phone_info.get("primaryPhoneCallingCode") or ""
    if phone:
        formatted = f"{calling_code}{phone}".replace(" ", "")
        phone = formatted if formatted.startswith("+") else f"+{formatted.lstrip('+')}"
    email = (record.get("emails") or {}).get("primaryEmail")

    updates = {
        "name": full_name or None,
        "email": email,
        "phone_number": phone,
        "custom_attributes": {
            "twenty_id": record.get("id"),
            "company_id": record.get("companyId"),
        },
    }

    async with httpx.AsyncClient() as client:
        result = await client.put(
            f"{CHATWOOT_API_URL}/accounts/1/contacts/{chatwoot_id}",
            headers={
                "Content-Type": "application/json",
                "api_access_token": CHATWOOT_BOT_ACCESS_TOKEN,
            },
            json=updates,
            timeout=HTTP_TIMEOUT,
        )
        print("🔄 Twenty webhook response:", result.status_code, result.text)

    return {"status": "updated"}

@app.post("/bot")
async def bot(request: Request):
    data = await request.json()
    convo = data.get("conversation", {}) or {}
    assignee_id = (convo.get("meta", {}) or {}).get("assignee", {}) or {}
    assignee_id = assignee_id.get("id")
    print("🤖 Bot webhook:", data)

    if assignee_id:
        print("❌ Ignoring conversation assigned to someone.")
        return {"status": "ignored conversation assigned"}

    # 1. Must be a message creation event.
    if data.get("event") != "message_created":
        # print("❌ Ignoring non-message event:", data.get("event"))
        return {"status": "ignored_event"}

    # 2. MUST be 'incoming' (from user). This reliably prevents the infinite loop.
    if data.get("message_type") != "incoming":
        # print("❌ Ignoring outgoing or internal message.")
        return {"status": "ignored_outgoing"}

    # 3. Ensure a sender exists to prevent KeyError later
    if "sender" not in data:
        # print("❌ Ignoring message with no sender.")
        return {"status": "ignored_no_sender"}

    account_id = data["account"]["id"]
    conversation_id = data["conversation"]["id"]

    user_id = str(data["sender"]["id"])
    text = data.get("content", "") or ""

    state = SESSIONS.get(user_id) or initial_state()
    state, reply, status = handle_input(state, text)
    SESSIONS[user_id] = state

    # print("🤖 Bot reply:", reply)
    # print("🤖 Bot status:", status)
    # print("🤖 Bot state:", state)


    # Post reply once (Chatwoot will emit an 'outgoing' webhook; we ignore it above)
    async with httpx.AsyncClient() as client:
        if reply == "human_agent":
            print("🤖 Routing to human agent")
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
            return {"status": "handoff"}

        await send_message(
            client=client,
            api_url=CHATWOOT_API_URL,
            access_token=CHATWOOT_BOT_ACCESS_TOKEN,
            account_id=account_id,
            conversation_id=conversation_id,
            content=reply,
            private=False,
        )

    return {"status": "success"}
