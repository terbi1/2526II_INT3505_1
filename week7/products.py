from flask import jsonify
import product_model as model

def get_all():
    products = model.find_all()
    return jsonify(products), 200

def get_one(product_id):
    product = model.find_by_id(product_id)
    if not product:
        return {"message": "Không tìm thấy sản phẩm"}, 404
    return jsonify(product), 200

def create(body):
    product_id = model.insert(body)
    return {"message": "Tạo thành công", "id": product_id}, 201

def update(product_id, body):
    updated = model.update_by_id(product_id, body)
    if not updated:
        return {"message": "Không tìm thấy sản phẩm"}, 404
    return {"message": "Cập nhật thành công"}, 200

def delete(product_id):
    deleted = model.delete_by_id(product_id)
    if not deleted:
        return {"message": "Không tìm thấy sản phẩm"}, 404
    return {"message": "Xóa thành công"}, 200