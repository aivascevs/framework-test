"""A small order store used by the demonstrator scenarios.

Synthetic data only. The module uses the Python standard library so that the
evaluation scenarios can change it without new runtime dependencies.
"""
from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass

LOG = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_email TEXT NOT NULL,
    amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
    refunded INTEGER NOT NULL DEFAULT 0
)
"""


@dataclass(frozen=True)
class Order:
    id: int
    customer_email: str
    amount_cents: int
    refunded: bool


def mask_email(email: str) -> str:
    """Return a form of the e-mail address that is safe to write to logs."""
    name, _, domain = email.partition("@")
    if not domain:
        return "***"
    return f"{name[:1]}***@{domain}"


class OrderStore:
    def __init__(self, path: str = ":memory:") -> None:
        self._db = sqlite3.connect(path)
        self._db.execute(SCHEMA)

    def create(self, customer_email: str, amount_cents: int) -> Order:
        if amount_cents <= 0:
            raise ValueError("amount_cents must be positive")
        cur = self._db.execute(
            "INSERT INTO orders (customer_email, amount_cents) VALUES (?, ?)",
            (customer_email, amount_cents),
        )
        self._db.commit()
        LOG.info("order %s created for %s", cur.lastrowid, mask_email(customer_email))
        return self.get(cur.lastrowid)

    def get(self, order_id: int) -> Order:
        row = self._db.execute(
            "SELECT id, customer_email, amount_cents, refunded FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()
        if row is None:
            raise KeyError(order_id)
        return Order(row[0], row[1], row[2], bool(row[3]))

    def refund(self, order_id: int) -> Order:
        order = self.get(order_id)
        if order.refunded:
            raise ValueError("order already refunded")
        self._db.execute("UPDATE orders SET refunded = 1 WHERE id = ?", (order_id,))
        self._db.commit()
        LOG.info("order %s refunded", order_id)
        return self.get(order_id)
