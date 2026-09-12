from unittest.mock import patch

import pytest
import main


# Keep the test data in one place instead of repeating it in every test.
SAMPLE_PRODUCTS = [
    {
        "name": "Wireless Mouse",
        "category": "electronics",
        "price": 799,
        "currency": "INR",
        "stock": 25
    },
    {
        "name": "Mechanical Keyboard",
        "category": "electronics",
        "price": 2499,
        "currency": "INR",
        "stock": 12
    },
    {
        "name": "USB-C Hub",
        "category": "electronics",
        "price": 1299,
        "currency": "INR",
        "stock": 8
    },
    {
        "name": "Laptop Stand",
        "category": "accessories",
        "price": 1499,
        "currency": "INR",
        "stock": 20
    },
]


@pytest.fixture
def mock_products():
    # Give each test a fake Mongo collection instead of using the real database.
    with patch("main.products_collection") as mock_col:
        yield mock_col


def test_search_all_products(mock_products):
    mock_products.find.return_value = SAMPLE_PRODUCTS

    result = main.search_products()

    assert len(result) == 4
    assert result[0]["name"] == "Wireless Mouse"

    mock_products.find.assert_called_once_with(
        {},
        {"_id": 0}
    )


def test_search_product_by_name(mock_products):
    mock_products.find.return_value = [SAMPLE_PRODUCTS[0]]

    result = main.search_products(query="mouse")

    assert len(result) == 1
    assert result[0]["name"] == "Wireless Mouse"

    mock_products.find.assert_called_once_with(
        {
            "name": {
                "$regex": "mouse",
                "$options": "i"
            }
        },
        {"_id": 0}
    )


def test_product_search_is_case_insensitive(mock_products):
    mock_products.find.return_value = [SAMPLE_PRODUCTS[0]]

    result = main.search_products(query="MOUSE")

    assert len(result) == 1

    mock_products.find.assert_called_once_with(
        {
            "name": {
                "$regex": "MOUSE",
                "$options": "i"
            }
        },
        {"_id": 0}
    )


def test_search_by_category(mock_products):
    mock_products.find.return_value = SAMPLE_PRODUCTS[:3]

    result = main.search_products(category="electronics")

    assert len(result) == 3

    mock_products.find.assert_called_once_with(
        {
            "category": {
                "$regex": "^electronics$",
                "$options": "i"
            }
        },
        {"_id": 0}
    )


def test_search_by_max_price(mock_products):
    mock_products.find.return_value = [
        SAMPLE_PRODUCTS[0],
        SAMPLE_PRODUCTS[2],
        SAMPLE_PRODUCTS[3]
    ]

    result = main.search_products(max_price=1500)

    assert len(result) == 3

    mock_products.find.assert_called_once_with(
        {
            "price": {
                "$lte": 1500
            }
        },
        {"_id": 0}
    )


def test_search_by_name_and_max_price(mock_products):
    mock_products.find.return_value = [SAMPLE_PRODUCTS[0]]

    result = main.search_products(
        query="mouse",
        max_price=1000
    )

    assert len(result) == 1

    mock_products.find.assert_called_once_with(
        {
            "name": {
                "$regex": "mouse",
                "$options": "i"
            },
            "price": {
                "$lte": 1000
            }
        },
        {"_id": 0}
    )


def test_no_product_matches_filters(mock_products):
    mock_products.find.return_value = []

    result = main.search_products(
        query="keyboard",
        max_price=2000
    )

    assert result == []


def test_regex_characters_are_escaped(mock_products):
    mock_products.find.return_value = []

    result = main.search_products(query=".*")

    assert result == []

    # Make sure .* is treated literally, not as regex.
    mock_products.find.assert_called_once_with(
        {
            "name": {
                "$regex": r"\.\*",
                "$options": "i"
            }
        },
        {"_id": 0}
    )