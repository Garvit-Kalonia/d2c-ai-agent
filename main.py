import json
import re

import ollama

from database import products_collection, orders_collection
from rag import search_policy


def search_products(query="", category="", max_price=None):
    """
    Search the product catalog using the filters provided.
    """
    mongo_query = {}

    if query:
        # Escape the search text so things like .* don't act as regex.
        mongo_query["name"] = {
            "$regex": re.escape(query),
            "$options": "i"
        }

    if category:
        # Match the whole category rather than partial category names.
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


def lookup_order(order_id: str):
    """
    Look up an order by its ID.
    """
    order = orders_collection.find_one(
        {"order_id": order_id},
        {"_id": 0}
    )

    if not order:
        return {
            "error": "Order not found"
        }

    return order


def cancel_order(order_id: str):
    """
    Cancel an order only if it is still in Processing status.
    """
    order = orders_collection.find_one(
        {"order_id": order_id},
        {"_id": 0}
    )

    if not order:
        return {
            "success": False,
            "error": "Order not found"
        }

    status = order["status"]

    if status != "Processing":
        return {
            "success": False,
            "error": f"Order cannot be cancelled from status: {status}"
        }

    # Check the status again as part of the update.
    # This prevents us from cancelling an order that changed state
    # between the lookup above and this update.
    result = orders_collection.update_one(
        {
            "order_id": order_id,
            "status": "Processing"
        },
        {
            "$set": {
                "status": "Cancelled"
            }
        }
    )

    if result.modified_count == 1:
        return {
            "success": True,
            "order_id": order_id,
            "status": "Cancelled"
        }

    return {
        "success": False,
        "error": "Order could not be cancelled because its status changed."
    }


SYSTEM_PROMPT = """
You are a helpful customer support agent for a D2C e-commerce store.

Use tools whenever you need information from the product catalog,
orders, or store policies. Do not guess information that can be
looked up.

PRODUCTS:
- Use search_products for product searches.
- You can filter by product name, category, or maximum price.

ORDERS:
- Use lookup_order when the user asks about a specific order.
- Ask for the order ID if one is required but has not been provided.

POLICIES:
- Use search_policy for questions about store policies such as
  returns, refunds, shipping, warranties, and cancellations.
- If a policy question depends on a specific product, look up the
  product first when necessary.

CANCELLATIONS:
- An order can only be cancelled while its status is Processing.
- Never call cancel_order unless the user has clearly asked to cancel
  the order and the order ID is known.
- Ask for confirmation before cancelling an order.
- Do not claim that an order was cancelled unless cancel_order
  actually reports success.

Keep responses clear and reasonably concise.
"""


tools = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": (
                "Search the product catalog by name, category, "
                "or maximum price."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Text to search for in the product name."
                        )
                    },
                    "category": {
                        "type": "string",
                        "description": (
                            "Product category such as electronics "
                            "or accessories."
                        )
                    },
                    "max_price": {
                        "type": "number",
                        "description": (
                            "Maximum product price in INR."
                        )
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_order",
            "description": (
                "Look up an order using its order ID and return "
                "its current status and details."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": (
                            "Order ID such as ORD1001."
                        )
                    }
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_policy",
            "description": (
                "Search the store's policies for information about "
                "returns, refunds, shipping, warranties, or cancellations."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "The policy information to look for."
                        )
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_order",
            "description": (
                "Cancel an order that is currently Processing. "
                "Do not use this tool until the user has confirmed "
                "that they want to cancel the order."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": (
                            "The order ID of the order to cancel."
                        )
                    }
                },
                "required": ["order_id"]
            }
        }
    }
]


TOOL_MAP = {
    "search_products": search_products,
    "lookup_order": lookup_order,
    "search_policy": search_policy,
    "cancel_order": cancel_order,
}


def execute_tool(call):
    """
    Run the Python function requested by the model.
    """
    name = call.function.name
    args = call.function.arguments

    # Ollama can return the arguments as either a dict or JSON text.
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            return {
                "error": "Invalid tool arguments."
            }

    if not isinstance(args, dict):
        return {
            "error": "Tool arguments must be an object."
        }

    if name not in TOOL_MAP:
        return {
            "error": f"Unknown tool: {name}"
        }

    try:
        return TOOL_MAP[name](**args)
    except Exception as e:
        # Keep tool failures inside the agent loop instead of crashing it.
        print(f"Tool error in {name}: {e}")
        return {
            "error": f"Failed to execute tool: {name}"
        }


MAX_ITERATIONS = 5


def run_agent():
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    print("D2C Customer Support Agent")
    print("Type 'exit' or 'quit' to stop.\n")

    while True:
        user_input = input("User: ").strip()

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        messages.append({
            "role": "user",
            "content": user_input
        })

        iterations = 0

        while iterations < MAX_ITERATIONS:
            iterations += 1

            response = ollama.chat(
                model="qwen3:4b",
                messages=messages,
                tools=tools
            )

            assistant_msg = response.message
            messages.append(assistant_msg)

            # No tool call means the model is ready to answer the user.
            if not assistant_msg.tool_calls:
                print(f"\nAgent: {assistant_msg.content}\n")
                break

            for call in assistant_msg.tool_calls:
                print(
                    f" -> {call.function.name}"
                    f"({call.function.arguments})"
                )

                tool_output = execute_tool(call)

                messages.append({
                    "role": "tool",
                    "content": json.dumps(tool_output)
                })

        if iterations >= MAX_ITERATIONS:
            print(
                "\nSystem: Reached the maximum number of tool calls "
                "for this request.\n"
            )


if __name__ == "__main__":
    run_agent()