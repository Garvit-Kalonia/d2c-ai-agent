from unittest.mock import patch

import pytest
import main


SAMPLE_ORDERS = {
    "ORD1001": {
        "order_id": "ORD1001",
        "customer": "Rahul",
        "status": "Shipped",
        "items": ["Wireless Mouse"],
        "total": 799,
    },
    "ORD1002": {
        "order_id": "ORD1002",
        "customer": "Priya",
        "status": "Processing",
        "items": ["Mechanical Keyboard"],
        "total": 2499,
    },
}


@pytest.fixture
def mock_orders():
    with patch("main.orders_collection") as mock_col:
        yield mock_col


@pytest.mark.parametrize("order_id", ["ORD1001", "ORD1002"])
def test_lookup_existing_order(mock_orders, order_id):
    expected_order = SAMPLE_ORDERS[order_id]
    mock_orders.find_one.return_value = expected_order

    result = main.lookup_order(order_id)

    assert result == expected_order

    mock_orders.find_one.assert_called_once_with(
        {"order_id": order_id},
        {"_id": 0}
    )


def test_lookup_nonexistent_order_returns_error(mock_orders):
    mock_orders.find_one.return_value = None

    result = main.lookup_order("ORD9999")

    assert result == {
        "error": "Order not found"
    }

    mock_orders.find_one.assert_called_once_with(
        {"order_id": "ORD9999"},
        {"_id": 0}
    )
