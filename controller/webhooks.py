"""Webhook controller functions."""

import requests


def process_chatwoot_webhook(payload: dict):
    print("☎️ Chatwoot webhook payload received:", payload)

    if not payload.get("event", "").startswith("contact_"):
        return {"message": "Not a contact event"}
    if not payload.get("phone_number") and not payload.get("email"):
        return {"message": "No phone number or email detected"}

    n8n = requests.post("http://host.docker.internal:5678/webhook/chatwoot", json=payload).json()
    n8ntest = requests.post("http://host.docker.internal:5678/webhook-test/chatwoot", json=payload).json()
    print("🔄 N8N webhook:", n8n)
    print("🔄 N8N test webhook:", n8ntest)
    return {"message": "Chatwoot webhook processed"}


def process_twenty_webhook(payload: dict):
    print("👩‍🔧 Twenty webhook:", payload)

    if payload.get("record", {}).get("deletedAt"):
        print("🧹 Deletion detected, skipping n8n call.")
        return {"message": "Deletion detected, skipping n8n call."}

    n8n = requests.post("http://host.docker.internal:5678/webhook/twenty", json=payload).json()
    n8ntest = requests.post("http://host.docker.internal:5678/webhook-test/twenty", json=payload).json()
    print("🔄 N8N webhook:", n8n)
    print("🔄 N8N test webhook:", n8ntest)
    return {"message": "Twenty webhook processed"}


__all__ = ["process_chatwoot_webhook", "process_twenty_webhook"]
