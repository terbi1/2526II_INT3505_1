from flask import Blueprint, request, jsonify, url_for
from models.database import orders_db, products_db, new_id, now
from routes.event_routes import publish_event

hateoas_bp = Blueprint('hateoas', __name__)


def build_order_links(order):
    oid    = order['id']
    status = order['status']
    links  = {}

    links['self'] = {
        "href":   f"/api/v1/orders/{oid}",
        "method": "GET",
        "rel":    "self"
    }

    links['collection'] = {
        "href":   "/api/v1/orders",
        "method": "GET",
        "rel":    "collection"
    }

    if order.get('product_id') in products_db:
        links['product'] = {
            "href":   f"/api/v1/products/{order['product_id']}",
            "method": "GET",
            "rel":    "related"
        }

    if status == 'pending':
        links['pay'] = {
            "href":        f"/api/v1/orders/{oid}/pay",
            "method":      "POST",
            "rel":         "action",
            "description": "Thanh toán đơn hàng"
        }
        links['cancel'] = {
            "href":        f"/api/v1/orders/{oid}/cancel",
            "method":      "POST",
            "rel":         "action",
            "description": "Hủy đơn hàng"
        }

    elif status == 'paid':
        links['ship'] = {
            "href":        f"/api/v1/orders/{oid}/ship",
            "method":      "POST",
            "rel":         "action",
            "description": "Đánh dấu đã giao cho đơn vị vận chuyển"
        }

    elif status == 'shipped':
        links['deliver'] = {
            "href":        f"/api/v1/orders/{oid}/deliver",
            "method":      "POST",
            "rel":         "action",
            "description": "Xác nhận đã giao hàng thành công"
        }

    return links


def order_response(order):
    return {
        **order,
        "_links": build_order_links(order)
    }

@hateoas_bp.route('', methods=['GET'])
def list_orders():
    orders = [order_response(o) for o in orders_db.values()]
    return jsonify({
        "data": orders,
        "_links": {
            "self":   {"href": "/api/v1/orders", "method": "GET"},
            "create": {"href": "/api/v1/orders", "method": "POST",
                       "description": "Tạo order mới"}
        }
    })


@hateoas_bp.route('/<order_id>', methods=['GET'])
def get_order(order_id):
    order = orders_db.get(order_id)
    if not order:
        return jsonify({"error": "not_found"}), 404
    return jsonify(order_response(order))


@hateoas_bp.route('', methods=['POST'])
def create_order():
    data = request.get_json()
    pid  = data.get('product_id')

    if not pid or pid not in products_db:
        return jsonify({"error": "product không tồn tại"}), 404

    oid = new_id()
    product = products_db[pid]
    quantity = int(data.get('quantity', 1))

    order = {
        "id":         oid,
        "product_id": pid,
        "quantity":   quantity,
        "status":     "pending",       # luôn bắt đầu từ pending
        "total":      product['price'] * quantity,
        "user_id":    data.get('user_id', 'anonymous'),
        "created_at": now(),
    }
    orders_db[oid] = order

    resp = jsonify(order_response(order))
    resp.status_code = 201
    resp.headers['Location'] = f'/api/v1/orders/{oid}'
    return resp

@hateoas_bp.route('/<order_id>/pay', methods=['POST'])
def pay_order(order_id):
    return _transition(order_id,
                       from_status='pending',
                       to_status='paid',
                       event_type='order.paid')


@hateoas_bp.route('/<order_id>/ship', methods=['POST'])
def ship_order(order_id):
    return _transition(order_id,
                       from_status='paid',
                       to_status='shipped',
                       event_type='order.shipped')


@hateoas_bp.route('/<order_id>/deliver', methods=['POST'])
def deliver_order(order_id):
    return _transition(order_id,
                       from_status='shipped',
                       to_status='delivered',
                       event_type='order.delivered')


@hateoas_bp.route('/<order_id>/cancel', methods=['POST'])
def cancel_order(order_id):
    order = orders_db.get(order_id)
    if not order:
        return jsonify({"error": "not_found"}), 404

    if order['status'] not in ('pending', 'paid'):
        return jsonify({
            "error":   "invalid_transition",
            "message": f"Không thể hủy order ở trạng thái '{order['status']}'",
            "_links":  build_order_links(order)
        }), 409

    order['status']     = 'cancelled'
    order['updated_at'] = now()
    orders_db[order_id] = order

    publish_event('order.cancelled', order)

    return jsonify(order_response(order))


def _transition(order_id, from_status, to_status, event_type):
    order = orders_db.get(order_id)
    if not order:
        return jsonify({"error": "not_found"}), 404

    if order['status'] != from_status:
        return jsonify({
            "error":   "invalid_transition",
            "message": f"Cần trạng thái '{from_status}', hiện tại là '{order['status']}'",
            "_links":  build_order_links(order)
        }), 409

    order['status']     = to_status
    order['updated_at'] = now()
    orders_db[order_id] = order

    publish_event(event_type, order)

    return jsonify(order_response(order))
