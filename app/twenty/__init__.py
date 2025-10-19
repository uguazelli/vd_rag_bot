"""Helpers for interacting with the Twenty CRM API."""

from .people import (
    create_or_update_people,
    get_people_by_id,
    get_people_chatwoot_id,
)

__all__ = [
    "create_or_update_people",
    "get_people_by_id",
    "get_people_chatwoot_id",
]
