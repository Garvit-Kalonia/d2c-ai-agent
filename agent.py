from ollama import chat

MODEL = "qwen3:4b"



# This is the tool Qwen will be allowed to use
def search_products(category: str = "", max_price: int = 0):
    results = products

    if category:
        results = [
            product for product in results
            if product["category"].lower() == category.lower()
        ]

    if max_price > 0:
        results = [
            product for product in results
            if product["price"] <= max_price
        ]

    return results


# Conversation with the model
messages = [
    {
        "role": "user",
        "content": "Do you have any electronics under ₹1500?"
    }
]


# First call: ask Qwen what it wants to do
response = chat(
    model=MODEL,
    messages=messages,
    tools=[search_products]
)

print("MODEL RESPONSE:")
print(response.message.content)

print("\nTOOL CALLS:")
print(response.message.tool_calls)


# If Qwen decided to use a tool, execute it
if response.message.tool_calls:

    messages.append(response.message)

    for call in response.message.tool_calls:

        if call.function.name == "search_products":

            arguments = call.function.arguments

            result = search_products(**arguments)

            print("\nTOOL RESULT:")
            print(result)

            messages.append({
                "role": "tool",
                "tool_name": call.function.name,
                "content": str(result)
            })


    # Second call: give the tool result back to Qwen
    final_response = chat(
        model=MODEL,
        messages=messages,
        tools=[search_products]
    )

    print("\nFINAL ANSWER:")
    print(final_response.message.content)