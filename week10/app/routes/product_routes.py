"""
app/routes/product_routes.py - Example business API with full observability
"""
import logging
import random
import time
from flask import Blueprint, request, jsonify, g

from app.auth import jwt_required, role_required
from app.rate_limiter import limiter
from monitoring.circuit_breaker import get_or_create, CircuitOpenError

logger = logging.getLogger(__name__)

products_bp = Blueprint("products", __name__, url_prefix="/api/products")

# Circuit breaker for the (simulated) external inventory service
inventory_cb = get_or_create(
    "inventory_service",
    failure_threshold=3,
    recovery_timeout=15.0,
)

# In-memory product store (replace with DB in production)
PRODUCTS = {
    1: {"id": 1, "name": "Laptop Pro X", "price": 1299.99, "stock": 50},
    2: {"id": 2, "name": "Wireless Mouse", "price": 29.99, "stock": 200},
    3: {"id": 3, "name": "Mechanical Keyboard", "price": 89.99, "stock": 75},
    4: {"id": 4, "name": "4K Monitor", "price": 449.99, "stock": 30},
    5: {"id": 5, "name": "USB-C Hub", "price": 39.99, "stock": 120},
}


def _call_inventory_service(product_id: int) -> dict:
    """
    Simulates calling an external inventory service.
    Randomly fails ~30 % of the time to demo the circuit breaker.
    """
    time.sleep(0.05)  # Simulate network latency
    if random.random() < 0.3:
        raise ConnectionError("Inventory service unreachable")
    product = PRODUCTS.get(product_id)
    return {"stock": product["stock"] if product else 0, "source": "live"}


# ── Endpoints ────────────────────────────────────────────────────────────────

@products_bp.route("", methods=["GET"])
@limiter.limit("60 per minute")        # Public list endpoint
def list_products():
    """
    GET /api/products
    Public endpoint — returns all products.
    Rate limit: 60 req/min.
    """
    logger.info("Product list requested", extra={"ip": request.remote_addr})
    return jsonify({"products": list(PRODUCTS.values()), "count": len(PRODUCTS)}), 200


@products_bp.route("/<int:product_id>", methods=["GET"])
@limiter.limit("120 per minute")
def get_product(product_id: int):
    """
    GET /api/products/<id>
    Returns product detail + live stock via circuit-breaker-protected external call.
    """
    product = PRODUCTS.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404

    # Attempt live inventory check through circuit breaker
    stock_info = {"stock": product["stock"], "source": "cached"}
    cb_status = "closed"

    try:
        stock_info = inventory_cb.call(_call_inventory_service, product_id)
        cb_status = "closed"
    except CircuitOpenError as e:
        cb_status = "open"
        logger.warning(f"Circuit open — using cached stock for product {product_id}")
    except Exception as e:
        cb_status = inventory_cb.state.value
        logger.error(f"Inventory service error for product {product_id}: {e}")

    return jsonify({
        **product,
        "stock_info": stock_info,
        "circuit_breaker": cb_status,
    }), 200


@products_bp.route("", methods=["POST"])
@jwt_required
@role_required("admin")
@limiter.limit("20 per minute")        # Tighter limit for write operations
def create_product():
    """
    POST /api/products
    Protected: admin JWT required.
    Rate limit: 20 req/min.
    """
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    price = data.get("price")
    stock = data.get("stock", 0)

    if not name or price is None:
        return jsonify({"error": "name and price are required"}), 400

    if not isinstance(price, (int, float)) or price < 0:
        return jsonify({"error": "price must be a non-negative number"}), 400

    new_id = max(PRODUCTS.keys()) + 1
    PRODUCTS[new_id] = {"id": new_id, "name": name, "price": price, "stock": stock}

    logger.info(
        "Product created",
        extra={"product_id": new_id, "user": g.current_user},
    )
    return jsonify(PRODUCTS[new_id]), 201


@products_bp.route("/<int:product_id>", methods=["DELETE"])
@jwt_required
@role_required("admin")
@limiter.limit("10 per minute")
def delete_product(product_id: int):
    """DELETE /api/products/<id> — admin only."""
    if product_id not in PRODUCTS:
        return jsonify({"error": "Product not found"}), 404

    deleted = PRODUCTS.pop(product_id)
    logger.info(
        "Product deleted",
        extra={"product_id": product_id, "user": g.current_user},
    )
    return jsonify({"deleted": deleted}), 200
