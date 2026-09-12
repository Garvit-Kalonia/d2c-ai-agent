from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")

db = client["d2c_agent"]

products_collection = db["products"]
orders_collection = db["orders"]

print("Connected to MongoDB")

