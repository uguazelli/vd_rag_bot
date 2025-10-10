from fastapi import FastAPI, Request
# from app.menu import initial_state, handle_input
from app.chatwoot.handleContactUpdated import handleContactCreated
from app.chatwoot.handoff import perform_handoff, send_message
from app.rag_engine.rag import initial_state, handle_input
import httpx, os

app = FastAPI()
SESSIONS = {}

# Defaults are cheap/solid; override via env if you want
BOT_ACCESS_TOKEN  = os.getenv("BOT_ACCESS_TOKEN")
CHATWOOT_API_URL = os.getenv("CHATWOOT_API_URL", "http://localhost:3000/api/v1")
HANDOFF_PUBLIC_REPLY = os.getenv(
    "HANDOFF_PUBLIC_REPLY", "Ok, please hold on while I connect you with a human agent."
)
HANDOFF_PRIVATE_NOTE = os.getenv(
    "HANDOFF_PRIVATE_NOTE", "Bot routed the conversation for human follow-up."
)
HANDOFF_PRIORITY = os.getenv("HANDOFF_PRIORITY", "high")

@app.get("/health")
async def health():
    print("🤖 Health check", flush=True)
    return {"status": "True"}

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    # print("🤖 Webhook:", data)
    handleContactCreated(data)
    return {"status": "ok"}

@app.post("/bot")
async def bot(request: Request):
    data = await request.json()
    convo = data.get("conversation", {}) or {}
    assignee_id = (convo.get("meta", {}) or {}).get("assignee", {}) or {}
    assignee_id = assignee_id.get("id")

    if assignee_id:
        print("❌ Ignoring conversation assigned to someone.")
        return {"status": "ignored conversation assigned"}

    # 1. Must be a message creation event.
    if data.get("event") != "message_created":
        print("❌ Ignoring non-message event:", data.get("event"))
        return {"status": "ignored_event"}

    # 2. MUST be 'incoming' (from user). This reliably prevents the infinite loop.
    if data.get("message_type") != "incoming":
        print("❌ Ignoring outgoing or internal message.")
        return {"status": "ignored_outgoing"}

    # 3. Ensure a sender exists to prevent KeyError later
    if "sender" not in data:
        print("❌ Ignoring message with no sender.")
        return {"status": "ignored_no_sender"}

    account_id = data["account"]["id"]
    conversation_id = data["conversation"]["id"]

    user_id = str(data["sender"]["id"])
    text = data.get("content", "") or ""

    state = SESSIONS.get(user_id) or initial_state()
    state, reply, status = handle_input(state, text)
    SESSIONS[user_id] = state

    print("🤖 Bot reply:", reply)
    print("🤖 Bot status:", status)
    print("🤖 Bot state:", state)


    # Post reply once (Chatwoot will emit an 'outgoing' webhook; we ignore it above)
    async with httpx.AsyncClient() as client:
        if reply == "human_agent":
            await perform_handoff(
                client=client,
                account_id=account_id,
                conversation_id=conversation_id,
                api_url=CHATWOOT_API_URL,
                access_token=BOT_ACCESS_TOKEN,
                public_reply=HANDOFF_PUBLIC_REPLY,
                private_note=HANDOFF_PRIVATE_NOTE,
                priority=HANDOFF_PRIORITY,
            )
            return {"status": "handoff"}

        await send_message(
            client=client,
            api_url=CHATWOOT_API_URL,
            access_token=BOT_ACCESS_TOKEN,
            account_id=account_id,
            conversation_id=conversation_id,
            content=reply,
            private=False,
        )

    return {"status": "success"}
