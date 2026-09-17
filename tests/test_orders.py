import pytest

from seed import seed_database
from database import orders_collection, products_collection
from agent.tools import (
    create_order,
    cancel_order,
    update_shipping_address,
    request_return,
)


@pytest.fixture(autouse=True)
def reset_database():
    # Each test gets the original demo data so mutations from one
    # test cannot affect the result of another test.
    seed_database()


def test_create_order():
    result = create_order(
        customer_id="CUST001",
        items=[
            {
                "product_id": "PROD017",
                "quantity": 2,
            }
        ],
        idempotency_key="test-create-001",
    )

    assert result["success"] is True
    assert result["order"]["customer_id"] == "CUST001"
    assert result["order"]["items"][0]["product_id"] == "PROD017"
    assert result["order"]["items"][0]["quantity"] == 2
    assert result["order"]["total"] == 15998


def test_create_order_rejects_empty_items():
    result = create_order(
        customer_id="CUST001",
        items=[],
    )

    assert result["success"] is False
    assert "at least one item" in result["error"]


def test_create_order_rejects_unknown_product():
    result = create_order(
        customer_id="CUST001",
        items=[
            {
                "product_id": "DOES_NOT_EXIST",
                "quantity": 1,
            }
        ],
    )

    assert result["success"] is False
    assert "Product not found" in result["error"]


def test_create_order_rejects_insufficient_stock():
    result = create_order(
        customer_id="CUST001",
        items=[
            {
                "product_id": "PROD017",
                "quantity": 999,
            }
        ],
    )

    assert result["success"] is False
    assert "Insufficient stock" in result["error"]


def test_cancel_processing_order():
    result = cancel_order(
        customer_id="CUST001",
        order_id="ORD1011",
    )

    assert result["success"] is True
    assert result["status"] == "Cancelled"

    order = orders_collection.find_one(
        {"order_id": "ORD1011"}
    )

    assert order["status"] == "Cancelled"


def test_cancel_shipped_order():
    result = cancel_order(
        customer_id="CUST002",
        order_id="ORD1002",
    )

    assert result["success"] is False
    assert "cannot be cancelled" in result["error"]


def test_update_shipping_address():
    address = {
        "street": "123 Test Street",
        "city": "New Delhi",
        "state": "Delhi",
        "postal_code": "110001",
        "country": "India",
    }

    result = update_shipping_address(
        customer_id="CUST001",
        order_id="ORD1011",
        address=address,
    )

    assert result["success"] is True
    assert result["shipping_address"] == address


def test_request_return():
    result = request_return(
        customer_id="CUST003",
        order_id="ORD1036",
        reason="Product is defective.",
    )

    assert result["success"] is True
    assert result["return_request"]["status"] == "Requested"