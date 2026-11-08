"""Token check for the sample application.

This path is High impact in policy-config/risk-paths.yaml, so changes here get
the smaller change budget and a specialist review. Synthetic tokens only. The
registry keeps SHA-256 digests, never the tokens themselves.
"""
from __future__ import annotations

import hashlib
import hmac
from enum import Enum

MIN_TOKEN_LENGTH = 16


class Role(str, Enum):
    CUSTOMER = "customer"
    STAFF = "staff"


class AuthError(Exception):
    """The caller is not authenticated, or has the wrong role."""


class TokenRegistry:
    def __init__(self) -> None:
        self._digests: dict[str, Role] = {}

    @staticmethod
    def _digest(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def register(self, token: str, role: Role) -> None:
        if len(token) < MIN_TOKEN_LENGTH:
            raise ValueError(f"token must have at least {MIN_TOKEN_LENGTH} characters")
        self._digests[self._digest(token)] = role

    def authenticate(self, token: str | None) -> Role:
        digest = self._digest(token or "")
        for known, role in self._digests.items():
            if hmac.compare_digest(known, digest):
                return role
        raise AuthError("invalid token")

    def require(self, token: str | None, role: Role) -> None:
        if self.authenticate(token) is not role:
            raise AuthError("forbidden")
