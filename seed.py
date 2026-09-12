from database import orders_collection, products_collection
from data import orders, products


def seed_database() -> None:
    """Reset MongoDB collections and insert the initial datasets."""
    products_collection.delete_many({})
    orders_collection.delete_many({})

    # Use copies so the seed data in data.py stays separate from MongoDB operations.
    if products:
        products_collection.insert_many([item.copy() for item in products])

    if orders:
        orders_collection.insert_many([item.copy() for item in orders])

    print("Database seeded successfully.")


if __name__ == "__main__":
    seed_database()
