from database import customers_collection, orders_collection


def verify_customer_access(customer_id, access_key):
    """
    Verify that the supplied access key belongs to the customer.
    """
    customer = customers_collection.find_one(
        {
            "customer_id": customer_id,
            "access_key": access_key
        },
        {
            "_id": 0,
            "customer_id": 1
        }
    )

    if not customer:
        return {
            "success": False,
            "error": "Invalid customer ID or access key."
        }

    return {
        "success": True,
        "customer_id": customer["customer_id"]
    }


def get_customer(customer_id):
    """
    Return customer information without exposing the access key.
    """
    customer = customers_collection.find_one(
        {"customer_id": customer_id},
        {
            "_id": 0,
            "access_key": 0
        }
    )

    if not customer:
        return {
            "error": "Customer not found."
        }

    return customer


def get_customer_orders(customer_id):
    """
    Return all orders belonging to a customer, newest first.
    """
    orders = orders_collection.find(
        {"customer_id": customer_id},
        {"_id": 0}
    ).sort("created_at", -1)

    return list(orders)