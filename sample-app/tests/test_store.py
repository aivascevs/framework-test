import pytest

from orders import OrderStore, mask_email


def test_create_and_get():
    store = OrderStore()
    order = store.create("ana@example.test", 1250)
    assert store.get(order.id) == order
    assert order.refunded is False


def test_amount_must_be_positive():
    with pytest.raises(ValueError):
        OrderStore().create("ana@example.test", 0)


def test_unknown_order():
    with pytest.raises(KeyError):
        OrderStore().get(999)


def test_refund_once_only():
    store = OrderStore()
    order = store.create("ana@example.test", 500)
    assert store.refund(order.id).refunded is True
    with pytest.raises(ValueError):
        store.refund(order.id)


def test_lookup_value_is_not_sql():
    store = OrderStore()
    store.create("ana@example.test", 500)
    with pytest.raises((KeyError, ValueError, TypeError)):
        store.get("1 OR 1=1")


@pytest.mark.parametrize(
    "email, masked",
    [("ana@example.test", "a***@example.test"), ("not-an-email", "***")],
)
def test_mask_email(email, masked):
    assert mask_email(email) == masked


def test_logs_do_not_contain_email(caplog):
    caplog.set_level("INFO")
    OrderStore().create("ana@example.test", 700)
    assert "ana@example.test" not in caplog.text
