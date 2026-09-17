from seed import seed_database

from agent.tools import (
    verify_customer_access,
    lookup_order,
    cancel_order,
    update_shipping_address,
    request_return,
)


def setup_function():
    # Reset the database before each test so one mutation cannot
    # affect the security checks in another test.
    seed_database()


def test_valid_customer_access():
    result = verify_customer_access(
        customer_id="CUST001",
        access_key="0000",
    )

    assert result["success"] is True
    assert result["customer_id"] == "CUST001"


def test_invalid_access_key():
    result = verify_customer_access(
        customer_id="CUST001",
        access_key="wrong-key",
    )

    assert result["success"] is False


def test_unknown_customer():
    result = verify_customer_access(
        customer_id="DOES_NOT_EXIST",
        access_key="0000",
    )

    assert result["success"] is False


def test_customer_cannot_access_another_customers_order():
    result = lookup_order(
        order_id="ORD1002",
        customer_id="CUST001",
    )

    assert result["error"] == "Order not found."


def test_customer_can_access_own_order():
    result = lookup_order(
        order_id="ORD1011",
        customer_id="CUST001",
    )

    assert result["order_id"] == "ORD1011"
    assert result["customer_id"] == "CUST001"


def test_customer_cannot_cancel_another_customers_order():
    result = cancel_order(
        customer_id="CUST001",
        order_id="ORD1002",
    )

    assert result["success"] is False
    assert result["error"] == "Order not found."


def test_customer_cannot_update_another_customers_order():
    address = {
        "street": "123 Test Street",
        "city": "New Delhi",
        "state": "Delhi",
        "postal_code": "110001",
        "country": "India",
    }

    result = update_shipping_address(
        customer_id="CUST001",
        order_id="ORD1002",
        address=address,
    )

    assert result["success"] is False
    assert result["error"] == "Order not found."


def test_customer_cannot_request_return_for_another_customers_order():
    result = request_return(
        customer_id="CUST001",
        order_id="ORD1036",
        reason="Product is defective.",
    )

    assert result["success"] is False
    assert result["error"] == "Order not found."