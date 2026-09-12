from unittest.mock import patch

import pytest
import main


@pytest.fixture
def mock_orders():
    # Give each test a fake Mongo collection instead of touching the real database.
    with patch("main.orders_collection") as mock_col:
        yield mock_col


def test_cancel_processing_order(mock_orders):
    mock_orders.find_one.return_value = {
        "order_id": "ORD1002",
        "status": "Processing"
    }
    mock_orders.update_one.return_value.modified_count = 1

    result = main.cancel_order("ORD1002")

    assert result == {
        "success": True,
        "order_id": "ORD1002",
        "status": "Cancelled"
    }

    mock_orders.find_one.assert_called_once_with(
        {"order_id": "ORD1002"},
        {"_id": 0}
    )

    mock_orders.update_one.assert_called_once_with(
        {
            "order_id": "ORD1002",
            "status": "Processing"
        },
        {
            "$set": {
                "status": "Cancelled"
            }
        }
    )


@pytest.mark.parametrize("status", ["Shipped", "Delivered"])
def test_cannot_cancel_non_processing_orders(mock_orders, status):
    # If the order isn't Processing, we shouldn't even try the update.
    mock_orders.find_one.return_value = {
        "order_id": "ORD1001",
        "status": status
    }

    result = main.cancel_order("ORD1001")

    assert result["success"] is False
    assert f"status: {status}" in result["error"]
    mock_orders.update_one.assert_not_called()


def test_cancel_nonexistent_order(mock_orders):
    mock_orders.find_one.return_value = None

    result = main.cancel_order("ORD9999")

    assert result == {
        "success": False,
        "error": "Order not found"
    }

    mock_orders.update_one.assert_not_called()


def test_cancellation_fails_on_concurrent_status_change(mock_orders):
    mock_orders.find_one.return_value = {
        "order_id": "ORD1002",
        "status": "Processing"
    }

    # Pretend another update changed the order before ours could.
    mock_orders.update_one.return_value.modified_count = 0

    result = main.cancel_order("ORD1002")

    assert result["success"] is False
    assert "status changed" in result["error"]