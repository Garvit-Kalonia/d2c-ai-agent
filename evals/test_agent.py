import json

import pytest

import main
from data import orders, products
from database import orders_collection, products_collection


def reset_database():
    # Keep each evaluation independent from the state left by earlier runs.
    products_collection.delete_many({})
    orders_collection.delete_many({})

    products_collection.insert_many(
        [product.copy() for product in products]
    )

    orders_collection.insert_many(
        [order.copy() for order in orders]
    )


def run_test_agent(user_input):
    messages = [
        {
            "role": "system",
            "content": main.SYSTEM_PROMPT
        }
    ]

    return main.run_agent_turn(
        messages,
        user_input
    )


def get_tool_calls(result, tool_name):
    return [
        call
        for call in result["tool_calls"]
        if call["name"] == tool_name
    ]


def get_tool_args(call):
    # Ollama may return tool arguments as JSON text or as a dict.
    args = call["arguments"]

    if isinstance(args, str):
        return json.loads(args)

    return args


@pytest.fixture(autouse=True)
def reset_test_data():
    reset_database()


def test_agent_searches_products():
    result = run_test_agent(
        "Show me electronics under ₹1500."
    )

    calls = get_tool_calls(
        result,
        "search_products"
    )

    assert calls
    assert result["completed"] is True
    assert result["response"]

    # Check that the model extracted the important filters from the request.
    args = get_tool_args(calls[0])

    assert args["category"].lower() == "electronics"
    assert float(args["max_price"]) == 1500


def test_agent_looks_up_order():
    result = run_test_agent(
        "What's the status of ORD1001?"
    )

    calls = get_tool_calls(
        result,
        "lookup_order"
    )

    assert calls
    assert result["completed"] is True
    assert result["response"]

    # The model should pass the order ID from the user's request
    # rather than just calling the tool with some other value.
    args = get_tool_args(calls[0])

    assert args["order_id"] == "ORD1001"


def test_agent_does_not_cancel_without_confirmation():
    result = run_test_agent(
        "Can I cancel ORD1002?"
    )

    lookup_calls = get_tool_calls(
        result,
        "lookup_order"
    )

    cancel_calls = get_tool_calls(
        result,
        "cancel_order"
    )

    assert lookup_calls
    assert not cancel_calls
    assert result["completed"] is True
    assert result["response"]

    lookup_args = get_tool_args(
        lookup_calls[0]
    )

    assert lookup_args["order_id"] == "ORD1002"

    # Asking about cancellation should not change the order.
    order = orders_collection.find_one(
        {"order_id": "ORD1002"}
    )

    assert order["status"] == "Processing"


def test_agent_cancels_after_confirmation():
    messages = [
        {
            "role": "system",
            "content": main.SYSTEM_PROMPT
        }
    ]

    first_result = main.run_agent_turn(
        messages,
        "I want to cancel ORD1002."
    )

    first_lookup_calls = get_tool_calls(
        first_result,
        "lookup_order"
    )

    first_cancel_calls = get_tool_calls(
        first_result,
        "cancel_order"
    )

    assert first_lookup_calls
    assert not first_cancel_calls

    first_lookup_args = get_tool_args(
        first_lookup_calls[0]
    )

    assert first_lookup_args["order_id"] == "ORD1002"

    second_result = main.run_agent_turn(
        messages,
        "Yes, cancel it."
    )

    second_cancel_calls = get_tool_calls(
        second_result,
        "cancel_order"
    )

    assert second_cancel_calls
    assert second_result["completed"] is True

    # The confirmation should lead to cancellation of the same order
    # that was discussed in the previous turn.
    cancel_args = get_tool_args(
        second_cancel_calls[0]
    )

    assert cancel_args["order_id"] == "ORD1002"

    order = orders_collection.find_one(
        {"order_id": "ORD1002"}
    )

    assert order["status"] == "Cancelled"


def test_agent_does_not_cancel_shipped_order():
    result = run_test_agent(
        "Cancel ORD1001."
    )

    lookup_calls = get_tool_calls(
        result,
        "lookup_order"
    )

    cancel_calls = get_tool_calls(
        result,
        "cancel_order"
    )

    assert lookup_calls
    assert not cancel_calls
    assert result["completed"] is True

    lookup_args = get_tool_args(
        lookup_calls[0]
    )

    assert lookup_args["order_id"] == "ORD1001"

    # The agent should inspect the order before attempting the action.
    # Since this order is already shipped, it must remain unchanged.
    order = orders_collection.find_one(
        {"order_id": "ORD1001"}
    )

    assert order["status"] == "Shipped"
