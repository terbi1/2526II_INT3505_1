# Buổi 11-12: API Design Patterns — Flask Implementation

## Cấu trúc dự án

```
api_patterns/
├── app.py                          # Entry point, đăng ký blueprints
├── models/
│   └── database.py                 # In-memory DB (dict/list)
├── routes/
│   ├── crud_routes.py              # Pattern 1: CRUD
│   ├── query_routes.py             # Pattern 2: Query (Filter/Sort/Pagination)
│   ├── hateoas_routes.py           # Pattern 3: HATEOAS + State Machine
│   ├── event_routes.py             # Pattern 4: Event-driven (Pub/Sub)
│   ├── webhook_routes.py           # Pattern 5: Webhook (Delivery + Signature)
│   └── notification_routes.py      # Thực hành: Notification System
└── analysis/
    └── stripe_github_patterns.py   # Phân tích Stripe + GitHub API
```

## Khởi động

```bash
pip install flask
python app.py
# Server chạy tại http://localhost:5000
```

---

## PATTERN 1: CRUD

**Nguyên tắc**: Mỗi HTTP method = 1 thao tác dữ liệu.

| Method | URL | Action |
|--------|-----|--------|
| POST | /api/v1/products | Create |
| GET | /api/v1/products | Read list |
| GET | /api/v1/products/:id | Read one |
| PUT | /api/v1/products/:id | Replace (full) |
| PATCH | /api/v1/products/:id | Update (partial) |
| DELETE | /api/v1/products/:id | Delete |

```bash
# Tạo product
curl -X POST http://localhost:5000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{"name": "AirPods Pro", "category": "electronics", "price": 249, "stock": 80}'
# → 201 Created, Location: /api/v1/products/xxx

# Đọc list với pagination
curl "http://localhost:5000/api/v1/products?page=1&per_page=3"

# PATCH: chỉ update price, các field khác giữ nguyên
curl -X PATCH http://localhost:5000/api/v1/products/p001 \
  -H "Content-Type: application/json" \
  -d '{"price": 899.0}'

# DELETE → 204 No Content
curl -X DELETE http://localhost:5000/api/v1/products/p005
```

**PUT vs PATCH**: PUT thay toàn bộ (cần gửi đủ fields), PATCH thay một phần.

---

## PATTERN 2: QUERY

**Nguyên tắc**: URL params cho filter/sort/page. POST body cho query phức tạp.

```bash
# Simple query: filter + sort + projection
curl "http://localhost:5000/api/v1/search/products\
?category=electronics&min_price=100&max_price=1500\
&sort=price&order=asc&fields=id,name,price"

# Advanced query với AND/OR logic
curl -X POST http://localhost:5000/api/v1/search/products/advanced \
  -H "Content-Type: application/json" \
  -d '{
    "filters": {
      "AND": [
        {"field": "category", "op": "eq", "value": "electronics"},
        {
          "OR": [
            {"field": "price", "op": "lte", "value": 1000},
            {"field": "rating", "op": "gte", "value": 4.8}
          ]
        }
      ]
    },
    "sort": [{"field": "price", "order": "asc"}],
    "fields": ["name", "price", "rating"]
  }'

# Cursor-based pagination (scalable)
curl "http://localhost:5000/api/v1/search/products/cursor?limit=2"
# → trả next_cursor, dùng để lấy trang tiếp:
curl "http://localhost:5000/api/v1/search/products/cursor?after=p002&limit=2"
```

**Offset vs Cursor**:
- Offset: `?page=1000` → DB scan 10,000 rows → chậm với big data
- Cursor: `?after=id_xxx` → DB dùng index → luôn O(1)

---

## PATTERN 3: HATEOAS

**Nguyên tắc**: Response chứa `_links` cho phép client "follow" thay vì hard-code URLs. State machine: `pending → paid → shipped → delivered`.

```bash
# Xem order: response có _links với các actions khả dụng
curl http://localhost:5000/api/v1/orders/o001
# Response có: _links.pay, _links.cancel (vì status=pending)

# Follow link "pay" → transition sang trạng thái "paid"
curl -X POST http://localhost:5000/api/v1/orders/o001/pay
# Response có: _links.ship (vì giờ status=paid)

# Follow link "ship"
curl -X POST http://localhost:5000/api/v1/orders/o001/ship

# Tạo order mới
curl -X POST http://localhost:5000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{"product_id": "p002", "quantity": 1, "user_id": "u003"}'
```

**Tại sao HATEOAS?** Client không cần biết trước URL, server kiểm soát workflow. Thay đổi URL trên server → không break client.

---

## PATTERN 4: EVENT-DRIVEN

**Nguyên tắc**: Thay vì các component gọi trực tiếp nhau, mọi thứ qua Event Bus. Producer không biết consumer.

```bash
# Xem event store (audit log)
curl http://localhost:5000/api/v1/events

# Filter theo event type
curl "http://localhost:5000/api/v1/events?type=order.paid"

# Xem subscribers hiện tại
curl http://localhost:5000/api/v1/events/subscribers

# Publish event thủ công (để test)
curl -X POST http://localhost:5000/api/v1/events/publish \
  -H "Content-Type: application/json" \
  -d '{"type": "order.shipped", "data": {"order_id": "o001"}, "source": "manual"}'

# Replay events (Event Sourcing)
curl -X POST http://localhost:5000/api/v1/events/replay \
  -H "Content-Type: application/json" \
  -d '{"from_index": 0, "event_type": "order.paid"}'
```

**Event Sourcing concept**: Lưu events thay vì state. State = replay toàn bộ events. Dùng cho audit trail, undo/redo, debugging.

---

## PATTERN 5: WEBHOOK

**Nguyên tắc**: Server chủ động gọi HTTP đến URL của client khi có event. Client không cần polling.

```bash
# Đăng ký webhook (giống Stripe POST /v1/webhook_endpoints)
curl -X POST http://localhost:5000/api/v1/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://webhook.site/your-unique-id",
    "events": ["order.paid", "order.shipped"],
    "description": "Thông báo đơn hàng"
  }'
# → Trả signing_secret: "whsec_xxxx"

# Xem danh sách webhooks
curl http://localhost:5000/api/v1/webhooks

# Xem delivery history
curl http://localhost:5000/api/v1/webhooks/{webhook_id}/deliveries

# Gửi test event
curl -X POST http://localhost:5000/api/v1/webhooks/{webhook_id}/test

# Trigger một event để webhooks nhận
curl -X POST http://localhost:5000/api/v1/webhooks/trigger \
  -H "Content-Type: application/json" \
  -d '{"event_type": "order.paid", "data": {"order_id": "o003"}}'

# Nhận webhook từ bên ngoài (mô phỏng Stripe gọi vào)
curl -X POST http://localhost:5000/api/v1/webhooks/receive \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Signature: sha256=your-sig" \
  -H "X-Webhook-Source: stripe" \
  -d '{"type": "payment.succeeded", "data": {}}'
```

**Bảo mật Webhook** (HMAC-SHA256):
```python
import hmac, hashlib

def verify_webhook(payload_bytes, signature_header, secret):
    expected = "sha256=" + hmac.new(
        secret.encode(), payload_bytes, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)
    # hmac.compare_digest chống timing attack
```

---

## THỰC HÀNH: Notification System (Event + Webhook kết hợp)

```bash
# Setup notification preferences cho user
curl -X POST http://localhost:5000/api/v1/notifications/preferences \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "u001",
    "channels": {
      "webhook": {
        "url": "https://webhook.site/xxx",
        "events": ["order.paid", "order.shipped", "order.delivered"]
      },
      "in_app": true
    }
  }'

# Demo full flow: action → event → notification → webhook delivery
curl -X POST http://localhost:5000/api/v1/notifications/demo/full-flow \
  -H "Content-Type: application/json" \
  -d '{"user_id": "u001", "order_id": "o002"}'

# Xem in-app notifications
curl "http://localhost:5000/api/v1/notifications?user_id=u001"

# Đánh dấu đã đọc
curl -X POST http://localhost:5000/api/v1/notifications/{notif_id}/read
```

**Full Flow**:
```
User Action (REST API)
    ↓
publish_event("order.paid", data)
    ↓
Event Store (persist) + Event Bus (dispatch)
    ↓ (subscribers)
    ├── Notification Handler → tạo in-app notification
    └── Webhook Engine → HTTP POST đến subscriber URLs
                              ↓ (nếu fail)
                         Retry với exponential backoff
```

---

## Phân tích Stripe vs GitHub

Chạy để xem phân tích đầy đủ:
```bash
python analysis/stripe_github_patterns.py
```

**Stripe patterns nổi bật**:
- Dùng POST cho update (không dùng PATCH) — lý do lịch sử
- Cursor pagination: `?starting_after=ch_xxx`
- Idempotency-Key header: chống charge 2 lần
- Expand pattern: `?expand[]=customer` (như GraphQL nhưng đơn giản)

**GitHub patterns nổi bật**:
- HATEOAS đầy đủ: mọi nested object có `url` field
- Pagination qua Link header (RFC 5988)
- REST v3 + GraphQL v4 song song

---

## Khi nào dùng REST vs gRPC vs GraphQL

| | REST | gRPC | GraphQL |
|---|---|---|---|
| **Dùng khi** | Public API, CRUD, Webhook | Internal microservices, Streaming | Complex graph, Mobile với bandwidth thấp |
| **Caching** | Tốt (HTTP cache) | Khó | Phức tạp |
| **Typing** | Không bắt buộc | Strict (Protobuf) | Strict (Schema) |
| **Performance** | Tốt | Tốt nhất | Trung bình |
| **Learning curve** | Thấp | Cao | Trung bình |
| **Browser support** | Native | gRPC-web (workaround) | Native |
