from agent.tools import search_products, get_product


def test_search_products_by_keyword():
    results = search_products(query="wireless mouse")

    assert len(results) == 1
    assert results[0]["name"] == "Logitech MX Master 3S"


def test_search_products_across_product_fields():
    results = search_products(query="gaming mouse")

    assert len(results) == 1
    assert results[0]["name"] == "Razer DeathAdder V3"


def test_search_products_by_category():
    results = search_products(category="Phones")

    assert results
    assert all(product["category"] == "Phones" for product in results)


def test_search_products_by_max_price():
    results = search_products(max_price=10000)

    assert results
    assert all(product["price"] <= 10000 for product in results)


def test_search_products_with_combined_filters():
    results = search_products(
        query="wireless",
        category="Mice",
        max_price=10000
    )

    assert len(results) == 1
    assert results[0]["name"] == "Logitech MX Master 3S"


def test_get_product():
    result = get_product("PROD017")

    assert result["name"] == "Logitech MX Master 3S"
    assert result["brand"] == "Logitech"
    assert result["price"] == 7999