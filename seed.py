import json
from datetime import datetime
from pathlib import Path

from database import (
    customers_collection,
    products_collection,
    orders_collection,
)


DATA_DIR = Path(__file__).parent / "data"


def load_json(filename):
    """Load a JSON file from the data directory."""
    with open(DATA_DIR / filename, "r", encoding="utf-8") as file:
        return json.load(file)


def convert_dates(order):
    """Convert ISO timestamp strings in an order into Python datetime objects."""

    date_fields = [
        "created_at",
        "updated_at",
        "cancelled_at",
        "estimated_delivery",
    ]

    for field in date_fields:
        if order.get(field):
            order[field] = datetime.fromisoformat(order[field])

    return order


def seed_database():
    customers = load_json("customers.json")
    products = load_json("products.json")
    orders = load_json("orders.json")

    # Clear the old demo data so every seed starts from a known state.
    customers_collection.delete_many({})
    products_collection.delete_many({})
    orders_collection.delete_many({})

    if customers:
        customers_collection.insert_many(customers)

    if products:
        products_collection.insert_many(products)

    if orders:
        orders = [convert_dates(order) for order in orders]
        orders_collection.insert_many(orders)

    print(
        f"Database seeded successfully: "
        f"{len(customers)} customers, "
        f"{len(products)} products, "
        f"{len(orders)} orders."
    )


if __name__ == "__main__":
    seed_database()