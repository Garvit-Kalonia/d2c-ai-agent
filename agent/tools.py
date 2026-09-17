from tools.customers import (
    verify_customer_access,
    get_customer,
    get_customer_orders,
)

from tools.products import (
    search_products,
    get_product,
)

from tools.orders import (
    lookup_order,
    create_order,
    cancel_order,
    update_shipping_address,
    request_return,
)

from rag import search_policy


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Search the product catalog using optional filters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Product name or keyword to search for."
                    },
                    "category": {
                        "type": "string",
                        "description": "Product category to filter by."
                    },
                    "max_price": {
                        "type": "number",
                        "description": "Maximum product price."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_product",
            "description": "Look up a specific product by product ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "The product ID."
                    }
                },
                "required": ["product_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_order",
            "description": "Look up an order belonging to the authenticated customer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The order ID."
                    }
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_customer",
            "description": "Retrieve the authenticated customer's account information.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_customer_orders",
            "description": "Retrieve orders belonging to the authenticated customer.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_policy",
            "description": "Search the store policy for information relevant to the customer's question.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Question or topic to search for in the store policy."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_order",
            "description": "Create an order for the authenticated customer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "description": "Products and quantities to order.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "product_id": {
                                    "type": "string"
                                },
                                "quantity": {
                                    "type": "integer"
                                }
                            },
                            "required": [
                                "product_id",
                                "quantity"
                            ]
                        }
                    },
                    "idempotency_key": {
                        "type": "string",
                        "description": "Optional key used to safely retry the same order request."
                    }
                },
                "required": ["items"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_order",
            "description": "Cancel an eligible order belonging to the authenticated customer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The order ID to cancel."
                    }
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_shipping_address",
            "description": "Update the shipping address for an eligible order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The order ID."
                    },
                    "address": {
                        "type": "object",
                        "properties": {
                            "street": {"type": "string"},
                            "city": {"type": "string"},
                            "state": {"type": "string"},
                            "postal_code": {"type": "string"},
                            "country": {"type": "string"}
                        },
                        "required": [
                            "street",
                            "city",
                            "state",
                            "postal_code",
                            "country"
                        ]
                    }
                },
                "required": ["order_id", "address"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "request_return",
            "description": "Request a return for an eligible delivered order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The order ID."
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for requesting the return."
                    }
                },
                "required": [
                    "order_id",
                    "reason"
                ]
            }
        }
    }
]

# Maps the tool names exposed to Qwen to the actual Python functions.
# The LLM only chooses a tool name and arguments; it never executes
# database operations directly.

TOOL_MAP = {
    "search_products": search_products,
    "get_product": get_product,
    "lookup_order": lookup_order,
    "get_customer": get_customer,
    "get_customer_orders": get_customer_orders,
    "search_policy": search_policy,
    "create_order": create_order,
    "cancel_order": cancel_order,
    "update_shipping_address": update_shipping_address,
    "request_return": request_return,
    "verify_customer_access": verify_customer_access,
}