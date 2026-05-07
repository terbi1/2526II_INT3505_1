from flask import Blueprint, request, jsonify
from utils.response import success_response, error_response
import uuid
import datetime

v2_bp = Blueprint("v2_payments", __name__, url_prefix="/api/v2")

# Dùng chung payments_db với v1 (thực tế nên dùng database thật)
from v1.payments import payments_db


# ---- Hằng số ----
SUPPORTED_CURRENCIES = {"VND", "USD", "EUR", "SGD"}

# Lưu idempotency keys: key → payment_id
idempotency_store = {}


def validate_payment_body(body: dict) -> tuple:
    """
    Validate request body cho v2.
    Returns: (errors: list, validated_data: dict)
    """
    errors = []
    validated = {}

    # Validate amount (integer, cents)
    if "amount" not in body:
        errors.append({"field": "amount", "message": "amount is required"})
    elif not isinstance(body["amount"], int):
        errors.append({
            "field": "amount",
            "message": "amount must be an integer (in cents/smallest unit). "
                       "Example: 50000 for 500.00 VND"
        })
    elif body["amount"] <= 0:
        errors.append({
            "field": "amount",
            "message": "amount must be greater than 0"
        })
    else:
        validated["amount_cents"] = body["amount"]

    # Validate currency (required trong v2)
    if "currency" not in body:
        errors.append({
            "field": "currency",
            "message": f"currency is required. Supported: {SUPPORTED_CURRENCIES}"
        })
    elif body["currency"] not in SUPPORTED_CURRENCIES:
        errors.append({
            "field": "currency",
            "message": f"Unsupported currency. Use one of: {SUPPORTED_CURRENCIES}"
        })
    else:
        validated["currency"] = body["currency"]

    # Optional fields
    validated["description"] = body.get("description", "")
    validated["metadata"] = body.get("metadata", {})
    
    return errors, validated


@v2_bp.route("/payments", methods=["GET"])
def list_payments():
    """
    [V2] Lấy danh sách thanh toán.
    
    Improvements vs v1:
    - amount là integer (cents) - chính xác hơn
    - Thêm trường currency
    - Thêm trường idempotency_key
    - Hỗ trợ pagination
    - Thêm trường metadata
    """
    # Pagination
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    per_page = min(per_page, 100)  # Giới hạn tối đa 100

    # Filter theo currency
    currency_filter = request.args.get("currency")
    
    all_payments = list(payments_db.values())
    
    # Apply filter
    if currency_filter:
        all_payments = [
            p for p in all_payments
            if p.get("currency", "").upper() == currency_filter.upper()
        ]
    
    # Pagination
    total = len(all_payments)
    start = (page - 1) * per_page
    end = start + per_page
    paginated = all_payments[start:end]

    # V2 response format
    v2_payments = []
    for p in paginated:
        v2_payments.append({
            "id": p["id"],
            "amount": p["amount_cents"],          # ✅ integer (cents)
            "currency": p.get("currency", "VND"),  # ✅ currency field
            "amount_formatted": _format_amount(   # ✅ human-readable
                p["amount_cents"],
                p.get("currency", "VND")
            ),
            "status": p["status"],
            "description": p.get("description", ""),
            "idempotency_key": p.get("idempotency_key"), # ✅ idempotency
            "metadata": p.get("metadata", {}),
            "created_at": p["created_at"]
        })

    return success_response(
        {"payments": v2_payments},
        meta={
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": -(-total // per_page)  # Ceiling division
            }
        }
    )


@v2_bp.route("/payments", methods=["POST"])
def create_payment():
    """
    [V2] Tạo thanh toán mới.
    
    Breaking changes từ v1:
    - amount: PHẢI là integer (cents), không còn float
    - currency: REQUIRED field mới
    
    New features:
    - Idempotency: Gửi header 'Idempotency-Key' để tránh duplicate
    - metadata: Lưu thông tin tùy chọn
    """
    body = request.get_json()
    
    if not body:
        return error_response("INVALID_REQUEST", "Request body is required")

    # ---- Idempotency Check ----
    idempotency_key = request.headers.get("Idempotency-Key")
    if idempotency_key:
        if idempotency_key in idempotency_store:
            # Trả về kết quả của request trước
            existing_id = idempotency_store[idempotency_key]
            existing_payment = payments_db.get(existing_id)
            if existing_payment:
                return success_response(
                    _format_v2_payment(existing_payment)
                ), 200  # 200, không phải 201 (đã tồn tại)

    # ---- Validation ----
    errors, validated = validate_payment_body(body)
    if errors:
        return error_response(
            "VALIDATION_ERROR",
            "Request validation failed",
            details={"fields": errors}
        )

    # ---- Tạo payment ----
    payment_id = str(uuid.uuid4())
    payment = {
        "id": payment_id,
        "amount_cents": validated["amount_cents"],
        "currency": validated["currency"],
        "status": "pending",
        "description": validated["description"],
        "metadata": validated["metadata"],
        "idempotency_key": idempotency_key,
        "created_at": datetime.datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.datetime.utcnow().isoformat() + "Z"
    }
    
    payments_db[payment_id] = payment
    
    # Lưu idempotency key
    if idempotency_key:
        idempotency_store[idempotency_key] = payment_id

    return success_response(_format_v2_payment(payment)), 201


@v2_bp.route("/payments/<payment_id>", methods=["GET"])
def get_payment(payment_id: str):
    """[V2] Lấy chi tiết một thanh toán."""
    payment = payments_db.get(payment_id)
    
    if not payment:
        return error_response(
            "NOT_FOUND",
            f"Payment '{payment_id}' not found",
            http_status=404
        )
    
    return success_response(_format_v2_payment(payment))


@v2_bp.route("/payments/<payment_id>", methods=["PATCH"])
def update_payment_status(payment_id: str):
    """[V2] Cập nhật trạng thái thanh toán (feature mới ở v2)."""
    payment = payments_db.get(payment_id)
    
    if not payment:
        return error_response(
            "NOT_FOUND",
            f"Payment '{payment_id}' not found",
            http_status=404
        )
    
    body = request.get_json() or {}
    new_status = body.get("status")
    
    VALID_TRANSITIONS = {
        "pending": ["processing", "cancelled"],
        "processing": ["completed", "failed"],
        "completed": [],
        "failed": [],
        "cancelled": []
    }
    
    current_status = payment["status"]
    allowed = VALID_TRANSITIONS.get(current_status, [])
    
    if new_status not in allowed:
        return error_response(
            "INVALID_TRANSITION",
            f"Cannot transition from '{current_status}' to '{new_status}'",
            details={"allowed_transitions": allowed}
        )
    
    payment["status"] = new_status
    payment["updated_at"] = datetime.datetime.utcnow().isoformat() + "Z"
    
    return success_response(_format_v2_payment(payment))


# ---- Helper functions ----

def _format_amount(cents: int, currency: str) -> str:
    """Format số tiền thành chuỗi có thể đọc được."""
    amount = cents / 100
    if currency == "VND":
        return f"{amount:,.0f} ₫"
    elif currency == "USD":
        return f"${amount:,.2f}"
    elif currency == "EUR":
        return f"€{amount:,.2f}"
    return f"{amount:,.2f} {currency}"


def _format_v2_payment(payment: dict) -> dict:
    """Chuẩn hóa output format cho v2."""
    return {
        "id": payment["id"],
        "amount": payment["amount_cents"],
        "currency": payment.get("currency", "VND"),
        "amount_formatted": _format_amount(
            payment["amount_cents"],
            payment.get("currency", "VND")
        ),
        "status": payment["status"],
        "description": payment.get("description", ""),
        "idempotency_key": payment.get("idempotency_key"),
        "metadata": payment.get("metadata", {}),
        "created_at": payment["created_at"],
        "updated_at": payment.get("updated_at", payment["created_at"])
    }