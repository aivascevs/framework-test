import secrets

import pytest

from auth import AuthError, Role, TokenRegistry
from orders import OrderStore
from orders.api import ValidationError, create_order, refund_order


@pytest.fixture
def env():
    registry = TokenRegistry()
    customer, staff = secrets.token_hex(16), secrets.token_hex(16)
    registry.register(customer, Role.CUSTOMER)
    registry.register(staff, Role.STAFF)
    return OrderStore(), registry, customer, staff


def test_create_returns_no_email(env):
    store, registry, customer, _ = env
    result = create_order(store, registry, customer, {"customer_email": "ana@example.test", "amount_cents": 900})
    assert result == {"id": 1, "amount_cents": 900, "refunded": False}


@pytest.mark.parametrize("payload", [
    {"customer_email": "not-an-email", "amount_cents": 900},
    {"customer_email": "ana@example.test", "amount_cents": 0},
    {"customer_email": "ana@example.test", "amount_cents": "900"},
    {"customer_email": "ana@example.test", "amount_cents": True},
    {"customer_email": "ana@example.test", "amount_cents": 10_000_000},
])
def test_create_validates_input(env, payload):
    store, registry, customer, _ = env
    with pytest.raises(ValidationError):
        create_order(store, registry, customer, payload)


def test_create_needs_a_token(env):
    store, registry, _, _ = env
    with pytest.raises(AuthError):
        create_order(store, registry, None, {"customer_email": "ana@example.test", "amount_cents": 900})


def test_only_staff_can_refund(env):
    store, registry, customer, staff = env
    order = create_order(store, registry, customer, {"customer_email": "ana@example.test", "amount_cents": 900})
    with pytest.raises(AuthError):
        refund_order(store, registry, customer, order["id"])
    assert refund_order(store, registry, staff, order["id"])["refunded"] is True
