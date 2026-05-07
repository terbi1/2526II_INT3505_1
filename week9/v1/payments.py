from flask import Blueprint, request, jsonify
from utils.deprecation import deprecated
from utils.response import success_response, error_response
import uuid

v1_bp = Blueprint("v1_payments", __name__, url_prefix="/api/v1")

# ---- Giả lập database ----
payments_db = {
    "126f5647-9721-4d1e-8452-789a715f33d1": {
        "id": "126f5647-9721-4d1e-8452-789a715f33d1",
        "amount_cents": 250000,
        "currency": "VND",
        "status": "completed",
        "description": "Thanh toán Grab #1",
        "created_at": "2024-04-10T14:22:15Z",
        "idempotency_key": None
    },
    "289b1c72-3c4d-4e5f-a1b2-c3d4e5f6g7h8": {
        "id": "289b1c72-3c4d-4e5f-a1b2-c3d4e5f6g7h8",
        "amount_cents": 1500000,
        "currency": "VND",
        "status": "pending",
        "description": "Mua trà sữa #2",
        "created_at": "2024-04-11T09:15:30Z",
        "idempotency_key": None
    },
    "3f8e9d1a-2b3c-4d5e-6f7g-8h9i0j1k2l3m": {
        "id": "3f8e9d1a-2b3c-4d5e-6f7g-8h9i0j1k2l3m",
        "amount_cents": 5000000,
        "currency": "VND",
        "status": "completed",
        "description": "Thanh toán hóa đơn điện #3",
        "created_at": "2024-04-12T10:00:00Z",
        "idempotency_key": None
    },
    "4a5b6c7d-8e9f-0a1b-2c3d-4e5f6g7h8i9j": {
        "id": "4a5b6c7d-8e9f-0a1b-2c3d-4e5f6g7h8i9j",
        "amount_cents": 120000,
        "currency": "VND",
        "status": "failed",
        "description": "Nạp thẻ điện thoại #4",
        "created_at": "2024-04-13T16:45:12Z",
        "idempotency_key": None
    },
    "5d6e7f8g-9h0i-1j2k-3l4m-5n6o7p8q9r0s": {
        "id": "5d6e7f8g-9h0i-1j2k-3l4m-5n6o7p8q9r0s",
        "amount_cents": 3450000,
        "currency": "VND",
        "status": "completed",
        "description": "Mua sắm Shopee #5",
        "created_at": "2024-04-14T21:10:05Z",
        "idempotency_key": None
    },
    "6g7h8i9j-0k1l-2m3n-4o5p-6q7r8s9t0u1v": {
        "id": "6g7h8i9j-0k1l-2m3n-4o5p-6q7r8s9t0u1v",
        "amount_cents": 99000,
        "currency": "VND",
        "status": "completed",
        "description": "Đăng ký Netflix #6",
        "created_at": "2024-04-15T08:30:45Z",
        "idempotency_key": None
    },
    "7i8j9k0l-1m2n-3o4p-5q6r-7s8t9u0v1w2x": {
        "id": "7i8j9k0l-1m2n-3o4p-5q6r-7s8t9u0v1w2x",
        "amount_cents": 25000000,
        "currency": "VND",
        "status": "pending",
        "description": "Thanh toán học phí #7",
        "created_at": "2024-04-16T11:20:00Z",
        "idempotency_key": None
    },
    "8k9l0m1n-2o3p-4q5r-6s7t-8u9v0w1x2y3z": {
        "id": "8k9l0m1n-2o3p-4q5r-6s7t-8u9v0w1x2y3z",
        "amount_cents": 450000,
        "currency": "VND",
        "status": "completed",
        "description": "Thanh toán Gym #8",
        "created_at": "2024-04-17T17:55:20Z",
        "idempotency_key": None
    },
    "9m0n1o2p-3q4r-5s6t-7u8v-9w0x1y2z3a4b": {
        "id": "9m0n1o2p-3q4r-5s6t-7u8v-9w0x1y2z3a4b",
        "amount_cents": 155000,
        "currency": "VND",
        "status": "failed",
        "description": "Mua đồ ăn tại WinMart #9",
        "created_at": "2024-04-18T12:05:10Z",
        "idempotency_key": None
    },
    "0o1p2q3r-4s5t-6u7v-8w9x-0y1z2a3b4c5d": {
        "id": "0o1p2q3r-4s5t-6u7v-8w9x-0y1z2a3b4c5d",
        "amount_cents": 750000,
        "currency": "VND",
        "status": "completed",
        "description": "Mua vé xem phim #10",
        "created_at": "2024-04-19T19:30:00Z",
        "idempotency_key": None
    },
    "1q2r3s4t-5u6v-7w8x-9y0z-1a2b3c4d5e6f": {
        "id": "1q2r3s4t-5u6v-7w8x-9y0z-1a2b3c4d5e6f",
        "amount_cents": 300000,
        "currency": "VND",
        "status": "completed",
        "description": "Gia hạn iCloud #11",
        "created_at": "2024-04-20T07:15:00Z",
        "idempotency_key": None
    },
    "2s3t4u5v-6w7x-8y9z-0a1b-2c3d4e5f6g7h": {
        "id": "2s3t4u5v-6w7x-8y9z-0a1b-2c3d4e5f6g7h",
        "amount_cents": 1250000,
        "currency": "VND",
        "status": "pending",
        "description": "Mua sách Tiki #12",
        "created_at": "2024-04-21T14:40:22Z",
        "idempotency_key": None
    },
    "3u5v6w7x-8y9z-0a1b-2c3d-4e5f6g7h8i9j": {
        "id": "3u5v6w7x-8y9z-0a1b-2c3d-4e5f6g7h8i9j",
        "amount_cents": 59000,
        "currency": "VND",
        "status": "completed",
        "description": "Thanh toán Spotify #13",
        "created_at": "2024-04-22T22:10:00Z",
        "idempotency_key": None
    },
    "4w7x8y9z-0a1b-2c3d-4e5f-6g7h8i9j0k1l": {
        "id": "4w7x8y9z-0a1b-2c3d-4e5f-6g7h8i9j0k1l",
        "amount_cents": 2200000,
        "currency": "VND",
        "status": "completed",
        "description": "Chuyển tiền ăn trưa #14",
        "created_at": "2024-04-23T11:50:35Z",
        "idempotency_key": None
    },
    "5y9z0a1b-2c3d-4e5f-6g7h-8i9j0k1l2m3n": {
        "id": "5y9z0a1b-2c3d-4e5f-6g7h-8i9j0k1l2m3n",
        "amount_cents": 850000,
        "currency": "VND",
        "status": "failed",
        "description": "Mua sắm Shopee #15",
        "created_at": "2024-04-24T15:25:00Z",
        "idempotency_key": None
    },
    "6a1b2c3d-4e5f-6g7h-8i9j-0k1l2m3n4o5p": {
        "id": "6a1b2c3d-4e5f-6g7h-8i9j-0k1l2m3n4o5p",
        "amount_cents": 10000000,
        "currency": "VND",
        "status": "completed",
        "description": "Gửi tiền tiết kiệm #16",
        "created_at": "2024-04-25T09:00:00Z",
        "idempotency_key": None
    },
    "7c3d4e5f-6g7h-8i9j-0k1l-2m3n4o5p6q7r": {
        "id": "7c3d4e5f-6g7h-8i9j-0k1l-2m3n4o5p6q7r",
        "amount_cents": 45000,
        "currency": "VND",
        "status": "completed",
        "description": "Mua trà sữa #17",
        "created_at": "2024-04-26T13:15:10Z",
        "idempotency_key": None
    },
    "8e5f6g7h-8i9j-0k1l-2m3n-4o5p6q7r8s9t": {
        "id": "8e5f6g7h-8i9j-0k1l-2m3n-4o5p6q7r8s9t",
        "amount_cents": 1200000,
        "currency": "VND",
        "status": "pending",
        "description": "Thanh toán Grab #18",
        "created_at": "2024-04-27T18:40:00Z",
        "idempotency_key": None
    },
    "9g7h8i9j-0k1l-2m3n-4o5p-6q7r8s9t0u1v": {
        "id": "9g7h8i9j-0k1l-2m3n-4o5p-6q7r8s9t0u1v",
        "amount_cents": 350000,
        "currency": "VND",
        "status": "completed",
        "description": "Mua sách Tiki #19",
        "created_at": "2024-04-28T10:05:45Z",
        "idempotency_key": None
    },
    "0i9j0k1l-2m3n-4o5p-6q7r-8s9t0u1v2w3x": {
        "id": "0i9j0k1l-2m3n-4o5p-6q7r-8s9t0u1v2w3x",
        "amount_cents": 210000,
        "currency": "VND",
        "status": "completed",
        "description": "Mua đồ ăn tại WinMart #20",
        "created_at": "2024-04-29T20:50:12Z",
        "idempotency_key": None
    }
}

@v1_bp.route("/payments", methods=["GET"])
@deprecated(
    sunset_date="2025-12-31",
    migration_guide="https://docs.example.com/api/migration/v1-to-v2",
    successor_version="v2"
)
def list_payments():
    """
    [V1 - DEPRECATED] Lấy danh sách thanh toán.
    
    Vấn đề của v1:
    - amount trả về dạng float (thiếu chính xác với tiền tệ)
    - Không có trường currency
    - Không hỗ trợ idempotency
    """
    payments = list(payments_db.values())
    
    # V1 format: amount là float
    v1_payments = []
    for p in payments:
        v1_payments.append({
            "id": p["id"],
            "amount": float(p["amount_cents"]) / 100,  # ⚠️ float - thiếu chính xác
            "status": p["status"],
            "description": p.get("description", ""),
            "created_at": p["created_at"]
            # ⚠️ Thiếu: currency, idempotency_key
        })
    
    return success_response({"payments": v1_payments})


@v1_bp.route("/payments", methods=["POST"])
@deprecated(
    sunset_date="2025-12-31",
    migration_guide="https://docs.example.com/api/migration/v1-to-v2",
    successor_version="v2"
)
def create_payment():
    """
    [V1 - DEPRECATED] Tạo thanh toán mới.
    
    Breaking changes khi lên v2:
    - amount: float → integer (cents)
    - Thêm required field: currency
    - Thêm optional field: idempotency_key
    """
    body = request.get_json()
    
    if not body:
        return error_response(
            "INVALID_REQUEST",
            "Request body is required"
        )
    
    # V1: Validate đơn giản
    if "amount" not in body:
        return error_response("MISSING_FIELD", "amount is required")
    
    if not isinstance(body["amount"], (int, float)) or body["amount"] <= 0:
        return error_response(
            "INVALID_AMOUNT",
            "amount must be a positive number"
        )
    
    # Lưu vào DB (convert float → cents để lưu)
    import datetime
    payment_id = str(uuid.uuid4())
    payment = {
        "id": payment_id,
        "amount_cents": int(float(body["amount"]) * 100),
        "currency": "VND",  # V1 hardcode currency
        "status": "pending",
        "description": body.get("description", ""),
        "created_at": datetime.datetime.utcnow().isoformat() + "Z",
        "idempotency_key": None  # V1 không hỗ trợ
    }
    payments_db[payment_id] = payment
    
    # V1 response format
    return success_response({
        "id": payment["id"],
        "amount": body["amount"],         # ⚠️ Trả về float gốc
        "status": payment["status"],
        "description": payment["description"],
        "created_at": payment["created_at"]
    }), 201


@v1_bp.route("/payments/<payment_id>", methods=["GET"])
@deprecated(
    sunset_date="2025-12-31",
    migration_guide="https://docs.example.com/api/migration/v1-to-v2",
    successor_version="v2"
)
def get_payment(payment_id: str):
    """[V1 - DEPRECATED] Lấy chi tiết một thanh toán."""
    payment = payments_db.get(payment_id)
    
    if not payment:
        return error_response(
            "NOT_FOUND",
            f"Payment {payment_id} not found",
            http_status=404
        )
    
    return success_response({
        "id": payment["id"],
        "amount": float(payment["amount_cents"]) / 100,  # ⚠️ float
        "status": payment["status"],
        "description": payment.get("description", ""),
        "created_at": payment["created_at"]
    })