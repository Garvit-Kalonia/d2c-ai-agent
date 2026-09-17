from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")

db = client["d2c_agent"]

customers_collection = db["customers"]
products_collection = db["products"]
orders_collection = db["orders"]