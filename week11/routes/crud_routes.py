from flask import Blueprint, request, jsonify
from models.database import products_db, new_id, now

crud_bp = Blueprint('crud', __name__)

@crud_bp.route('', methods=['POST'])
def create_product():
    data = request.get_json()

    required = ['name', 'category', 'price', 'stock']
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({
            "error": "validation_error",
            "message": f"Thiếu các trường bắt buộc: {missing}"
        }), 422

    pid = new_id()
    product = {
        "id":         pid,
        "name":       data['name'],
        "category":   data['category'],
        "price":      float(data['price']),
        "stock":      int(data['stock']),
        "rating":     data.get('rating', 0.0),
        "created_at": now(),
    }
    products_db[pid] = product

    response = jsonify(product)
    response.status_code = 201
    response.headers['Location'] = f'/api/v1/products/{pid}'
    return response


@crud_bp.route('', methods=['GET'])
def list_products():
    page     = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 3))

    all_products = list(products_db.values())
    total        = len(all_products)
    start        = (page - 1) * per_page
    end          = start + per_page
    items        = all_products[start:end]

    return jsonify({
        "data":       items,
        "pagination": {
            "page":       page,
            "per_page":   per_page,
            "total":      total,
            "total_pages": (total + per_page - 1) // per_page,
        }
    })

@crud_bp.route('/<product_id>', methods=['GET'])
def get_product(product_id):
    product = products_db.get(product_id)
    if not product:
        return jsonify({
            "error": "not_found",
            "message": f"Product '{product_id}' không tồn tại"
        }), 404

    return jsonify(product)

@crud_bp.route('/<product_id>', methods=['PUT'])
def replace_product(product_id):
    product = products_db.get(product_id)
    if not product:
        return jsonify({"error": "not_found"}), 404

    data = request.get_json()
    required = ['name', 'category', 'price', 'stock']
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({
            "error": "validation_error",
            "message": f"PUT yêu cầu đầy đủ tất cả fields. Thiếu: {missing}"
        }), 422

    updated = {
        "id":         product_id,
        "name":       data['name'],
        "category":   data['category'],
        "price":      float(data['price']),
        "stock":      int(data['stock']),
        "rating":     data.get('rating', 0.0),
        "created_at": product['created_at'],  # giữ nguyên
        "updated_at": now(),
    }
    products_db[product_id] = updated
    return jsonify(updated)

@crud_bp.route('/<product_id>', methods=['PATCH'])
def update_product(product_id):
    product = products_db.get(product_id)
    if not product:
        return jsonify({"error": "not_found"}), 404

    data = request.get_json()
    allowed_fields = {'name', 'category', 'price', 'stock', 'rating'}
    invalid = set(data.keys()) - allowed_fields
    if invalid:
        return jsonify({
            "error": "invalid_fields",
            "message": f"Không được phép cập nhật: {invalid}"
        }), 422

    product.update({k: v for k, v in data.items() if k in allowed_fields})
    product['updated_at'] = now()
    products_db[product_id] = product

    return jsonify(product)

@crud_bp.route('/<product_id>', methods=['DELETE'])
def delete_product(product_id):
    if product_id not in products_db:
        return jsonify({"error": "not_found"}), 404

    del products_db[product_id]
    return '', 204
