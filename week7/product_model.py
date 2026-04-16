from bson import ObjectId
from database import db

collection = db["products"]

def serialize(product):
    """Chuyển ObjectId → string để trả về JSON"""
    product["_id"] = str(product["_id"])
    return product

def find_all():
    return [serialize(p) for p in collection.find()]

def find_by_id(product_id):
    try:
        product = collection.find_one({"_id": ObjectId(product_id)})
        return serialize(product) if product else None
    except Exception:
        return None

def insert(data):
    result = collection.insert_one(data)
    return str(result.inserted_id)

def update_by_id(product_id, data):
    try:
        result = collection.update_one(
            {"_id": ObjectId(product_id)},
            {"$set": data}
        )
        return result.modified_count > 0
    except Exception:
        return False

def delete_by_id(product_id):
    try:
        result = collection.delete_one({"_id": ObjectId(product_id)})
        return result.deleted_count > 0
    except Exception:
        return False