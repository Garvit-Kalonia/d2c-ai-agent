from datetime import datetime, timezone
from uuid import uuid4

from database import orders_collection, products_collection


def _utc_now():
    """Return the current UTC time as an ISO string for tool responses."""
    return datetime.now(timezone.utc).isoformat()


def lookup_order(order_id, customer_id=None):
    """
    Look up an order by ID.

    When customer_id is provided, the query is ownership-scoped so
    the tool cannot expose another customer's order.
    """
    query = {
        "order_id": order_id
    }

    if customer_id:
        query["customer_id"] = customer_id

    order = orders_collection.find_one(
        query,
        {"_id": 0}
    )

    if not order:
        return {
            "error": "Order not found."
        }

    return order


def create_order(customer_id, items, idempotency_key=None):
    """
    Create an order after validating products and stock.

    Pricing is calculated from the current database values rather
    than anything supplied by the LLM.
    """
    if not items:
        return {
            "success": False,
            "error": "Order must contain at least one item."
        }

    # A retry with the same key should return the original order
    # instead of creating another order.
    if idempotency_key:
        existing_order = orders_collection.find_one(
            {"idempotency_key": idempotency_key},
            {"_id": 0}
        )

        if existing_order:
            return {
                "success": True,
                "already_exists": True,
                "order": existing_order
            }

    # Combine duplicate product lines before touching inventory.
    # Otherwise two lines for the same product could reserve stock
    # independently and make the final order harder to reason about.
    quantities = {}

    for item in items:
        product_id = item.get("product_id")
        quantity = item.get("quantity")

        if (
            not product_id
            or not isinstance(quantity, int)
            or isinstance(quantity, bool)
            or quantity <= 0
        ):
            return {
                "success": False,
                "error": (
                    "Each item must contain a valid product ID "
                    "and positive integer quantity."
                )
            }

        quantities[product_id] = quantities.get(product_id, 0) + quantity

    order_items = []
    subtotal = 0

    # Read current product information before reserving inventory.
    for product_id, quantity in quantities.items():
        product = products_collection.find_one(
            {
                "product_id": product_id,
                "is_active": True
            },
            {"_id": 0}
        )

        if not product:
            return {
                "success": False,
                "error": f"Product not found: {product_id}"
            }

        if product["stock"] < quantity:
            return {
                "success": False,
                "error": f"Insufficient stock for: {product['name']}"
            }

        item_subtotal = product["price"] * quantity
        subtotal += item_subtotal

        order_items.append({
            "product_id": product["product_id"],
            "name": product["name"],
            "quantity": quantity,
            "unit_price": product["price"],
            "subtotal": item_subtotal
        })

    shipping_fee = 0
    total = subtotal + shipping_fee
    iso_now = _utc_now()

    order_id = f"ORD-{uuid4().hex[:10].upper()}"

    order = {
        "order_id": order_id,
        "customer_id": customer_id,
        "status": "Processing",
        "payment_status": "Pending",
        "items": order_items,
        "subtotal": subtotal,
        "shipping_fee": shipping_fee,
        "total": total,
        "currency": "INR",
        "created_at": iso_now,
        "updated_at": iso_now
    }

    if idempotency_key:
        order["idempotency_key"] = idempotency_key

    reserved_items = []

    try:
        # The stock condition is part of the database update itself.
        # That closes the gap between "stock check" and "stock deduction"
        # where two simultaneous orders could otherwise both succeed.
        for item in order_items:
            result = products_collection.update_one(
                {
                    "product_id": item["product_id"],
                    "is_active": True,
                    "stock": {
                        "$gte": item["quantity"]
                    }
                },
                {
                    "$inc": {
                        "stock": -item["quantity"]
                    }
                }
            )

            if result.modified_count != 1:
                raise RuntimeError(
                    f"Unable to reserve stock for {item['product_id']}"
                )

            reserved_items.append(item)

        orders_collection.insert_one(dict(order))

    except Exception as exc:
        # If a later reservation or the order insert fails, put back
        # everything this request successfully reserved.
        for item in reserved_items:
            products_collection.update_one(
                {"product_id": item["product_id"]},
                {
                    "$inc": {
                        "stock": item["quantity"]
                    }
                }
            )

        return {
            "success": False,
            "error": f"Order could not be created: {exc}"
        }

    return {
        "success": True,
        "already_exists": False,
        "order": order
    }


def cancel_order(customer_id, order_id):
    """
    Cancel an order only when it belongs to the customer
    and is still in Processing status.
    """
    order = orders_collection.find_one(
        {
            "order_id": order_id,
            "customer_id": customer_id
        },
        {"_id": 0}
    )

    if not order:
        return {
            "success": False,
            "error": "Order not found."
        }

    if order["status"] == "Cancelled":
        return {
            "success": True,
            "already_cancelled": True,
            "order_id": order_id,
            "status": "Cancelled"
        }

    if order["status"] != "Processing":
        return {
            "success": False,
            "error": (
                f"Order cannot be cancelled from status: "
                f"{order['status']}"
            )
        }

    now = _utc_now()

    # Re-check Processing as part of the update. If another operation
    # changed the order after our lookup, this update simply won't match.
    result = orders_collection.update_one(
        {
            "order_id": order_id,
            "customer_id": customer_id,
            "status": "Processing"
        },
        {
            "$set": {
                "status": "Cancelled",
                "cancelled_at": now,
                "updated_at": now
            }
        }
    )

    if result.modified_count != 1:
        return {
            "success": False,
            "error": "Order could not be cancelled because its status changed."
        }

    # Cancellation releases the inventory that was reserved when
    # the order was created.
    for item in order.get("items", []):
        products_collection.update_one(
            {
                "product_id": item["product_id"]
            },
            {
                "$inc": {
                    "stock": item["quantity"]
                }
            }
        )

    return {
        "success": True,
        "already_cancelled": False,
        "order_id": order_id,
        "status": "Cancelled"
    }


def update_shipping_address(customer_id, order_id, address):
    """
    Update the shipping address for an eligible order.
    """
    if not isinstance(address, dict):
        return {
            "success": False,
            "error": "Address must be an object."
        }

    required_fields = [
        "street",
        "city",
        "state",
        "postal_code",
        "country"
    ]

    if any(not address.get(field) for field in required_fields):
        return {
            "success": False,
            "error": "Shipping address is missing required fields."
        }

    order = orders_collection.find_one(
        {
            "order_id": order_id,
            "customer_id": customer_id
        },
        {
            "_id": 0,
            "status": 1
        }
    )

    if not order:
        return {
            "success": False,
            "error": "Order not found."
        }

    if order["status"] != "Processing":
        return {
            "success": False,
            "error": (
                "Shipping address cannot be changed after "
                "the order has shipped."
            )
        }

    result = orders_collection.update_one(
        {
            "order_id": order_id,
            "customer_id": customer_id,
            "status": "Processing"
        },
        {
            "$set": {
                "shipping_address": address,
                "updated_at": _utc_now()
            }
        }
    )

    if result.modified_count != 1:
        return {
            "success": False,
            "error": "Shipping address could not be updated."
        }

    return {
        "success": True,
        "order_id": order_id,
        "shipping_address": address
    }


def request_return(customer_id, order_id, reason):
    """
    Create a return request for an eligible delivered order.
    """
    if not reason or not reason.strip():
        return {
            "success": False,
            "error": "A return reason is required."
        }

    order = orders_collection.find_one(
        {
            "order_id": order_id,
            "customer_id": customer_id
        },
        {
            "_id": 0,
            "status": 1,
            "return_request": 1
        }
    )

    if not order:
        return {
            "success": False,
            "error": "Order not found."
        }

    if order["status"] != "Delivered":
        return {
            "success": False,
            "error": "Only delivered orders can be returned."
        }

    if order.get("return_request"):
        return {
            "success": True,
            "already_requested": True,
            "return_request": order["return_request"]
        }

    return_request = {
        "status": "Requested",
        "reason": reason.strip(),
        "requested_at": _utc_now()
    }

    result = orders_collection.update_one(
        {
            "order_id": order_id,
            "customer_id": customer_id,
            "status": "Delivered",
            "return_request": {
                "$exists": False
            }
        },
        {
            "$set": {
                "return_request": return_request,
                "updated_at": _utc_now()
            }
        }
    )

    if result.modified_count != 1:
        return {
            "success": False,
            "error": "Return request could not be created."
        }

    return {
        "success": True,
        "already_requested": False,
        "order_id": order_id,
        "return_request": return_request
    }