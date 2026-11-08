"""Request handlers for the sample application.

Input arrives as a dict, for example parsed JSON from an HTTP request. The
handlers check the caller, validate the input and never return or log the
customer's e-mail address in clear text.
"""
from __future__ import annotations

import re

from auth import Role, TokenRegistry

from .store import OrderStore

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
MAX_AMOUNT_CENTS = 1_000_000


class ValidationError(ValueError):
    """The request payload is not valid."""


def _public(order) -> dict:
    return {"id": order.id, "amount_cents": order.amount_cents, "refunded": order.refunded}


def create_order(store: OrderStore, registry: TokenRegistry, token: str | None, payload: dict) -> dict:
    registry.authenticate(token)
    email = payload.get("customer_email")
    amount = payload.get("amount_cents")
    if not isinstance(email, str) or not EMAIL.match(email):
        raise ValidationError("customer_email is not a valid e-mail address")
    if not isinstance(amount, int) or isinstance(amount, bool) or not 0 < amount <= MAX_AMOUNT_CENTS:
        raise ValidationError(f"amount_cents must be an integer from 1 to {MAX_AMOUNT_CENTS}")
    return _public(store.create(email, amount))


def refund_order(store: OrderStore, registry: TokenRegistry, token: str | None, order_id: int) -> dict:
    registry.require(token, Role.STAFF)
    return _public(store.refund(order_id))
