from typing import Optional
import httpx

def _headers(access_token: str) -> dict[str, str]:
    return {"Content-Type": "application/json", "api_access_token": access_token}


async def send_message(
    *,
    client: httpx.AsyncClient,
    api_url: str,
    access_token: str,
    account_id: int,
    conversation_id: int,
    content: Optional[str],
    private: bool,
) -> None:
    if not content:
        return
    try:
        resp = await client.post(
            f"{api_url}/accounts/{account_id}/conversations/{conversation_id}/messages",
            headers=_headers(access_token),
            json={
                "content": content,
                "message_type": "outgoing",
                "private": private,
            },
        )
        if resp.status_code >= 300:
            print("❌ Error posting message:", resp.status_code, resp.text)
    except httpx.HTTPError as exc:
        print("❌ HTTP error posting message:", exc)


async def perform_handoff(
    *,
    client: httpx.AsyncClient,
    account_id: int,
    conversation_id: int,
    api_url: str,
    access_token: str,
    public_reply: Optional[str],
    private_note: Optional[str],
    priority: Optional[str],
) -> None:
    print(f"📡 Sending public reply and private note ")
    await send_message(
        client=client,
        api_url=api_url,
        access_token=access_token,
        account_id=account_id,
        conversation_id=conversation_id,
        content=public_reply,
        private=False,
    )
    await send_message(
        client=client,
        api_url=api_url,
        access_token=access_token,
        account_id=account_id,
        conversation_id=conversation_id,
        content=private_note,
        private=True,
    )

    try:
        print(
            f"🔧 Updating priority to {priority!r} "
            f"(account={account_id}, conversation={conversation_id})"
        )
        resp = await client.patch(
            f"{api_url}/accounts/{account_id}/conversations/{conversation_id}",
            headers=_headers(access_token),
            json={"priority": priority},
        )
        if resp.status_code >= 300:
            print("❌ Error setting priority:", resp.status_code, resp.text)
        else:
            print(
                f"✅ Priority set to {priority!r} "
                f"(account={account_id}, conversation={conversation_id})"
            )
    except httpx.HTTPError as exc:
        print("❌ HTTP error setting priority:", exc)
