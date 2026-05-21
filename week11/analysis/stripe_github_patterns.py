"""
analysis/stripe_github_patterns.py
=====================================
PHÂN TÍCH API: Stripe và GitHub
---------------------------------
Đây là bài phân tích patterns trong API thực tế của hai hệ thống lớn.
Không cần chạy (cần API key thật), đây là reference code và analysis.
"""

# ════════════════════════════════════════════════════════════════════════════
# PHẦN 1: PHÂN TÍCH STRIPE API PATTERNS
# ════════════════════════════════════════════════════════════════════════════

STRIPE_PATTERNS = """
══════════════════════════════════════════
STRIPE API — PATTERNS ANALYSIS
══════════════════════════════════════════

1. CRUD PATTERN
───────────────
Stripe dùng CRUD thuần cho resource management:

    POST   /v1/customers          → Create customer
    GET    /v1/customers/:id      → Read customer
    POST   /v1/customers/:id      → Update (Stripe dùng POST thay PATCH!)
    DELETE /v1/customers/:id      → Delete (thực ra là "archive")

Nhận xét đặc biệt:
- Stripe dùng POST cho update (không dùng PUT/PATCH)
  → Lý do lịch sử: tương thích với HTML form (chỉ có GET/POST)
  → Đây là ngoại lệ, REST chuẩn nên dùng PATCH/PUT
- DELETE không xóa thật mà set deleted=true (soft delete)
  → Quan trọng: dữ liệu tài chính không bao giờ xóa thật


2. QUERY PATTERN
────────────────
Stripe dùng cursor-based pagination nhất quán:

    GET /v1/charges?
        starting_after=ch_xxx   # cursor (ID của item cuối trang trước)
        ending_before=ch_yyy    # hoặc cursor cho chiều ngược
        limit=25                # 1-100, default 10
        created[gte]=1700000000 # filter theo Unix timestamp
        customer=cus_xxx        # filter theo customer

Nhận xét:
- Cursor-based pagination: scalable, consistent
- Filter bằng bracket notation: created[gte], amount[lt]
  → Thể hiện range query rõ ràng
- Không có page number → Stripe có hàng tỷ charges, offset không scale


3. WEBHOOK PATTERN (Stripe Events)
────────────────────────────────────
Stripe Events là implementation webhook hoàn chỉnh nhất trong ngành:

    // Đăng ký webhook
    POST /v1/webhook_endpoints
    {
        "url": "https://merchant.com/stripe-webhook",
        "enabled_events": ["payment_intent.succeeded", "charge.failed"]
    }

    // Payload Stripe gửi đến URL của merchant:
    {
        "id": "evt_xxx",
        "object": "event",
        "type": "payment_intent.succeeded",
        "data": {
            "object": { ...payment_intent_object... }
        },
        "livemode": true,
        "created": 1700000000
    }

    // Header để verify:
    Stripe-Signature: t=1700000000,v1=abc123...,v0=xyz789...

Bảo mật:
    import stripe
    def verify_stripe_webhook(payload, sig_header, secret):
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, secret)
            return event
        except stripe.error.SignatureVerificationError:
            return None  # reject

Retry logic:
- Stripe retry sau: 5s, 30s, 3m, 30m, 2h, 5h, 10h, 10h (6h), 10h (12h) x 3
- Tổng: ~72h, ~17 lần thử
- Nếu endpoint trả 2xx: success; bất kỳ code khác: retry
- Tip: luôn respond 200 ngay, xử lý bất đồng bộ sau


4. IDEMPOTENCY PATTERN (Stripe đặc trưng)
──────────────────────────────────────────
    POST /v1/charges
    Idempotency-Key: a-unique-key-from-client

→ Nếu request fail (network timeout), client gửi lại với cùng key
→ Stripe KHÔNG charge 2 lần, trả về kết quả của lần đầu
→ Pattern này cực quan trọng cho payment, không có trong REST chuẩn


5. EXPAND PATTERN (Projection nâng cao)
────────────────────────────────────────
    GET /v1/charges/ch_xxx?expand[]=customer&expand[]=payment_intent

→ Thay vì trả customer_id, trả toàn bộ customer object
→ Tương tự GraphQL nhưng đơn giản hơn
→ Giảm số round-trips cần thiết
"""


# ════════════════════════════════════════════════════════════════════════════
# PHẦN 2: PHÂN TÍCH GITHUB API PATTERNS
# ════════════════════════════════════════════════════════════════════════════

GITHUB_PATTERNS = """
══════════════════════════════════════════
GITHUB API — PATTERNS ANALYSIS
══════════════════════════════════════════

1. HATEOAS PATTERN
──────────────────
GitHub trả _links trong mọi response:

    GET /repos/octocat/hello-world
    Response:
    {
        "id": 1296269,
        "name": "Hello-World",
        "full_name": "octocat/Hello-World",
        "owner": {
            "login": "octocat",
            "url": "https://api.github.com/users/octocat"  ← HATEOAS link!
        },
        "url":        "https://api.github.com/repos/octocat/Hello-World",
        "forks_url":  "https://api.github.com/repos/octocat/Hello-World/forks",
        "issues_url": "https://api.github.com/repos/octocat/Hello-World/issues{/number}",
        "pulls_url":  "https://api.github.com/repos/octocat/Hello-World/pulls{/number}",
        "commits_url":"https://api.github.com/repos/octocat/Hello-World/commits{/sha}"
    }

Nhận xét:
- URL templates: issues_url có {/number} → RFC 6570 URI Template
- Client không cần biết cấu trúc URL, chỉ cần follow links
- "url" field ở mọi nested object → tự navigate được


2. WEBHOOK PATTERN (GitHub Events)
────────────────────────────────────
GitHub Webhooks hỗ trợ ~40 event types:

    // Tạo webhook cho repository
    POST /repos/{owner}/{repo}/hooks
    {
        "name": "web",
        "active": true,
        "events": ["push", "pull_request", "issues", "release"],
        "config": {
            "url":          "https://myapp.com/github-webhook",
            "content_type": "json",
            "secret":       "my-secret-key",
            "insecure_ssl": "0"
        }
    }

    // Headers GitHub gửi kèm:
    X-GitHub-Event: push
    X-GitHub-Delivery: 72d3162e-cc78-11e3-81ab-4c9367dc0958
    X-Hub-Signature-256: sha256=abc123...

    // Verify signature (Python):
    import hmac, hashlib
    def verify_github_webhook(payload_bytes, signature, secret):
        mac = hmac.new(secret.encode(), msg=payload_bytes, digestmod=hashlib.sha256)
        expected = 'sha256=' + mac.hexdigest()
        return hmac.compare_digest(expected, signature)

GitHub Ping Event:
- Khi tạo webhook, GitHub gửi ngay 1 "ping" event
- Endpoint phải respond 200 OK để confirm hoạt động


3. PAGINATION PATTERN
──────────────────────
GitHub dùng Link header (RFC 5988):

    GET /repos/octocat/hello-world/commits?per_page=30&page=2
    
    Response Headers:
    Link: <https://api.github.com/repos/octocat/hello-world/commits?page=3>; rel="next",
          <https://api.github.com/repos/octocat/hello-world/commits?page=1>; rel="prev",
          <https://api.github.com/repos/octocat/hello-world/commits?page=10>; rel="last",
          <https://api.github.com/repos/octocat/hello-world/commits?page=1>; rel="first"

Nhận xét:
- Links trong Header, không trong body (khác Stripe)
- rel="next/prev/first/last" → standard HATEOAS trong header
- GitHub cũng hỗ trợ cursor với "since" param cho commits


4. REST vs GraphQL (GitHub có CẢ HAI)
───────────────────────────────────────
GitHub v3 (REST):     https://api.github.com/
GitHub v4 (GraphQL):  https://api.github.com/graphql

REST endpoint:
    GET /repos/octocat/hello-world
    → Trả toàn bộ repo object (~50 fields)
    → Cần 3 round-trips để lấy repo + issues + labels

GraphQL query tương đương:
    query {
        repository(owner: "octocat", name: "hello-world") {
            name
            stargazerCount
            issues(first: 5, states: OPEN) {
                nodes {
                    title
                    labels(first: 3) { nodes { name } }
                }
            }
        }
    }
    → 1 request, lấy đúng data cần, không thừa

Khi nào GitHub khuyên dùng GraphQL?
- Cần data từ nhiều resources trong 1 request
- Muốn giảm payload (chỉ lấy fields cần thiết)
- Rate limit: GraphQL tính theo query cost, linh hoạt hơn
"""


# ════════════════════════════════════════════════════════════════════════════
# PHẦN 3: TỔNG KẾT - KHI NÀO DÙNG GÌ
# ════════════════════════════════════════════════════════════════════════════

DECISION_GUIDE = """
══════════════════════════════════════════
KHI NÀO DÙNG REST vs gRPC vs GraphQL
══════════════════════════════════════════

REST (với các patterns đã học)
───────────────────────────────
✅ Dùng khi:
  - Public API (mobile apps, 3rd party)
  - Resource-centric operations (CRUD)
  - Caching quan trọng (HTTP cache tốt với GET)
  - Team không cần training đặc biệt
  - Webhook integration với hệ thống ngoài

❌ Tránh khi:
  - Real-time communication (dùng WebSocket)
  - Cần fetch nhiều resources lồng nhau (N+1 problem)
  - Performance critical internal services

gRPC
─────
✅ Dùng khi:
  - Internal microservices communication
  - Performance critical (binary protocol, HTTP/2)
  - Strong typing quan trọng (Protobuf)
  - Streaming: server-side, client-side, bidirectional
  - Polyglot: Go, Java, Python, C++ cần giao tiếp

❌ Tránh khi:
  - Browser clients (gRPC-web là workaround, phức tạp)
  - Public API (developer experience kém)
  - Khi REST là đủ

GraphQL
────────
✅ Dùng khi:
  - Frontend cần flexibility cao (mobile vs web khác nhau)
  - Complex data graph với nhiều relationships
  - Muốn tránh over-fetching/under-fetching
  - Rapid iteration trên frontend mà không sửa backend

❌ Tránh khi:
  - Simple CRUD (GraphQL overhead không đáng)
  - Caching đơn giản cần (GraphQL cache phức tạp hơn)
  - File upload (cần workaround)
  - Team nhỏ không có bandwidth để setup

WebSocket / SSE (Server-Sent Events)
──────────────────────────────────────
✅ Dùng khi:
  - Real-time updates (chat, live dashboard)
  - Server push (thay thế long polling)
  - SSE: uni-directional server→client (đủ cho notification)

Kết luận thực tế:
  Hầu hết startup nên bắt đầu với REST + Webhook
  Scale lên → thêm gRPC cho internal services
  Khi frontend team lớn → xem xét GraphQL cho BFF layer
"""


def print_analysis():
    print(STRIPE_PATTERNS)
    print(GITHUB_PATTERNS)
    print(DECISION_GUIDE)


if __name__ == '__main__':
    print_analysis()
