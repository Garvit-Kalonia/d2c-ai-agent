#fake product database

products = [
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
    }
]

orders = [
    {
        "order_id": "ORD1001",
        "customer": "Rahul",
        "status": "Shipped",
        "items": ["Wireless Mouse"],
        "total": 799
    },
    {
        "order_id": "ORD1002",
        "customer": "Priya",
        "status": "Processing",
        "items": ["Mechanical Keyboard"],
        "total": 2499
    },
    {
        "order_id": "ORD1003",
        "customer": "Aman",
        "status": "Delivered",
        "items": ["USB-C Hub", "Laptop Stand"],
        "total": 2798
    }
]