import secrets

import pytest

from auth import AuthError, Role, TokenRegistry


def registry_with(role):
    registry, token = TokenRegistry(), secrets.token_hex(16)   # random synthetic token per test
    registry.register(token, role)
    return registry, token


def test_known_token_returns_role():
    registry, token = registry_with(Role.STAFF)
    assert registry.authenticate(token) is Role.STAFF


@pytest.mark.parametrize("token", [None, "", "x" * 32])
def test_unknown_token_is_rejected(token):
    registry, _ = registry_with(Role.STAFF)
    with pytest.raises(AuthError):
        registry.authenticate(token)


def test_short_token_cannot_be_registered():
    with pytest.raises(ValueError):
        TokenRegistry().register("short", Role.CUSTOMER)


def test_require_checks_the_role():
    registry, token = registry_with(Role.CUSTOMER)
    with pytest.raises(AuthError):
        registry.require(token, Role.STAFF)
