import re

from database import products_collection


def search_products(query="", category="", max_price=None):
    """
    Search the product catalog using optional filters.
    """

    mongo_query = {}

    if query:
        # Search each word independently so natural queries such as
        # "wireless mouse" can match information spread across the
        # product name, brand, category, and description.
        words = query.split()

        search_conditions = []

        for word in words:
            escaped_word = re.escape(word)

            search_conditions.append({
                "$or": [
                    {"name": {"$regex": escaped_word, "$options": "i"}},
                    {"brand": {"$regex": escaped_word, "$options": "i"}},
                    {"category": {"$regex": escaped_word, "$options": "i"}},
                    {"description": {"$regex": escaped_word, "$options": "i"}},
                ]
            })

        mongo_query["$and"] = search_conditions

    if category:
        mongo_query["category"] = {
            "$regex": f"^{re.escape(category)}$",
            "$options": "i"
        }

    if max_price is not None:
        try:
            max_price = float(max_price)

            if max_price >= 0:
                mongo_query["price"] = {
                    "$lte": max_price
                }

        except (ValueError, TypeError):
            pass

    return list(
        products_collection.find(
            mongo_query,
            {"_id": 0}
        )
    )


def get_product(product_id):
    """
    Look up a specific product by product ID.
    """
    product = products_collection.find_one(
        {"product_id": product_id},
        {"_id": 0}
    )

    if not product:
        return {
            "error": "Product not found."
        }

    return product