from flask import jsonify
import product_model as model

def get_all():
    products = model.find_all()
    return jsonify(products), 200

def get_one(product_id):
    product = model.find_by_id(product_id)
    if not product:
        return {"message": "Product not found"}, 404
    return jsonify(product), 200

def create(body):
    product_id = model.insert(body)
    return {"message": "Created successfully", "id": product_id}, 201

def update(product_id, body):
    updated = model.update_by_id(product_id, body)
    if not updated:
        return {"message": "Product not found"}, 404
    return {"message": "Updated successfully"}, 200

def delete(product_id):
    deleted = model.delete_by_id(product_id)
    if not deleted:
        return {"message": "Product not found"}, 404
    return {"message": "Delete successfully"}, 200