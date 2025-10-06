from fastapi import FastAPI, Request
# from app.menu import initial_state, handle_input
from app.rag import initial_state, handle_input

import httpx, os

app = FastAPI()
SESSIONS = {}

# Defaults are cheap/solid; override via env if you want
MODEL_ANSWER  = os.getenv("BOT_ACCESS_TOKEN",  "nS7yBjTg66L29cSUVypLQnGB")
MODEL_QUERIES = os.getenv("CHATWOOT_API_URL", "http://localhost:3000/api/v1")

# BOT_ACCESS_TOKEN = "nS7yBjTg66L29cSUVypLQnGB"
# CHATWOOT_API_URL = "http://localhost:3000/api/v1"

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/bot")
async def bot(request: Request):
    data = await request.json()
    convo = data.get("conversation", {}) or {}
    assignee_id = (convo.get("meta", {}) or {}).get("assignee", {}) or {}
    assignee_id = assignee_id.get("id")

    print("👤 assignee_id: ", assignee_id)

    if assignee_id:
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

    # Post reply once (Chatwoot will emit an 'outgoing' webhook; we ignore it above)
    async with httpx.AsyncClient() as client:
        if reply == "human_agent":
            # (A) post a short private note for agents (optional)
            # (B) call Chatwoot API: assign + toggle_bot
            # then return 200 without sending a public message
            return {"status": "handoff"}

        resp = await client.post(
            f"{CHATWOOT_API_URL}/accounts/{account_id}/conversations/{conversation_id}/messages",
            headers={"Content-Type": "application/json", "api_access_token": BOT_ACCESS_TOKEN},
            json={"content": reply, "message_type": "outgoing", "private": False},
        )
        if resp.status_code != 200:
            print("❌ Error posting message:", resp.status_code, resp.text)

    return {"status": "success"}
