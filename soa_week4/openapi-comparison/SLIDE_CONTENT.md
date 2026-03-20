# So sánh OpenAPI với các format tài liệu hóa API tương tự

**OpenAPI 3.0 · API Blueprint · RAML 1.0 · TypeSpec**
---
##  — API dùng để minh họa

Sử dụng một Book Management API đơn giản
```
GET    /v1/books              Danh sách sách
                              Query: ?genre=sci-fi&q=Frank&page=1&limit=20
                              Response: { data: Book[], pagination: {...} }

POST   /v1/books              Tạo sách mới
                              Body: { title, author, genre, isbn?, publishedYear?, price? }
                              Response 201: Book

GET    /v1/books/{id}         Chi tiết sách
PUT    /v1/books/{id}         Cập nhật toàn bộ (PUT semantics)
DELETE /v1/books/{id}         Xóa sách — trả về 204 No Content
```

---

##  Tiêu chí so sánh

Chúng ta sẽ nhìn mỗi format qua 6 góc độ:

| # | Tiêu chí | Câu hỏi thực tế |
|---|---|---|
| 1 | **Cú pháp** | Mất bao lâu để một developer mới viết được spec đầu tiên? |
| 2 | **Tái sử dụng** | Khi API có nhiều endpoints, có thể sử dụng lại được mẫu có sẵn  được không? |
| 3 | **Code generation** | Có sinh được client SDK hoặc server stub không? Chất lượng ra sao? |
---

##  — OpenAPI 3.0

### Tóm tắt

OpenAPI hiện là format phổ biến nhất để document REST API. Viết bằng YAML và JSON.

### Điểm mạnh

**Ecosystem:** Không có format nào có nhiều tool bằng OpenAPI.

**Tính phổ biến:** OpenAPI được sử dụng nhiều.

### Điểm yếu

**Dài dòng:** Một endpoint đơn giản trong OpenAPI cần nhiều dòng YAML khi viết đầy đủ.

### Ví dụ Book schema và GET /v1/books

```yaml
# Định nghĩa schema một lần, tái sử dụng qua $ref
components:
  schemas:
    Book:
      type: object
      required: [title, author, genre]   # ← bắt buộc phải có
      properties:
        id:
          type: integer
          readOnly: true                 # ← server gán, client không gửi
        title:
          type: string
          example: "Dune"
        genre:
          type: string
          enum: [fiction, non-fiction, sci-fi, history, biography]
        price:
          type: number
          nullable: true                 # ← có thể null
          example: 14.99

    ErrorResponse:
      type: object
      required: [code, message]
      properties:
        code:
          type: string
          example: "BOOK_NOT_FOUND"
        message:
          type: string

# Sử dụng schema trong endpoint
paths:
  /v1/books:
    get:
      summary: Danh sách sách
      parameters:
        - name: genre
          in: query
          schema:
            type: string
            enum: [fiction, non-fiction, sci-fi, history, biography]
        - name: q
          in: query
          description: Tìm trong title hoặc author (case-insensitive)
          schema:
            type: string
        - name: page
          in: query
          schema:
            type: integer
            default: 1
        - name: limit
          in: query
          schema:
            type: integer
            default: 20
            maximum: 100
      responses:
        '200':
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/Book'   # ← tái sử dụng qua $ref
                  pagination:
                    $ref: '#/components/schemas/Pagination'
        '400':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
```

# Sinh Python client
java -jar swagger-codegen-cli.jar generate \
  -i <đường_dẫn_tới_file_openapi> \
  -l <ngôn_ngữ_lập_trình> \
  -o <thư_mục_chứa_code_đầu_ra>

---

##  — API Blueprint: Viết docs như viết Markdown

### Tóm tắt

Triết lý cốt lõi: *API documentation nên đọc được như một tài liệu bình thường, không phải code.*

Viết bằng Markdown mở rộng (MSON — Markdown Syntax for Object Notation). File có đuôi `.apib`.

API Blueprint không còn được maintain tích cực từ khoảng năm 2019.

### Điểm mạnh

**Dễ đọc nhất:** Đây là điểm khác biệt lớn nhất so với 3 format còn lại.

**Narrative-friendly:** Vì dựa trên Markdown, bạn có thể viết đoạn văn giải thích context, use case, warning — xen kẽ với code.

### Điểm yếu

**Thiếu tính năng quan trọng:** Không có security scheme chuẩn, không có multiple server environments, không có schema reuse ở mức cao.

**Tooling đã lỗi thời:** Aglio vẫn hoạt động nhưng không còn được update.

**Code generation cực hạn chế:** Không thể sinh client SDK tốt từ `.apib`. 

### Ví dụ GET /v1/books

```markdown
FORMAT: 1A
HOST: http://localhost:5000

# Book Management API

API quản lý sách. Hỗ trợ tìm kiếm, lọc theo thể loại và phân trang.

## Data Structures

### Book
+ id: 1 (number, required) - Server-assigned ID
+ title: `Dune` (string, required)
+ author: `Frank Herbert` (string, required)
+ isbn: `978-0-441-01359-8` (string, optional) - Nullable
+ genre: `sci-fi` (enum[string], required)
    + Members
        + fiction
        + non-fiction
        + sci-fi
        + history
        + biography
+ publishedYear: 1965 (number, optional)
+ price: 14.99 (number, optional) - Nullable

# Group Books

## Danh sách sách [/v1/books{?genre,q,page,limit}]

### Lấy danh sách [GET]

Trả về sách đã lọc và phân trang.
Filter thứ tự: genre → q → paginate.
Tìm kiếm `q` là substring match, case-insensitive, trên cả title lẫn author.

+ Parameters
    + genre: `sci-fi` (string, optional) - Phải thuộc danh sách hợp lệ
    + q: `Frank` (string, optional) - Tìm trong title hoặc author
    + page: 1 (number, optional) - Tối thiểu 1
    + limit: 20 (number, optional) - Clamp vào [1, 100]

+ Response 200 (application/json)

    + Body

            {
                "data": [
                    {
                        "id": 1,
                        "title": "Dune",
                        "author": "Frank Herbert",
                        "genre": "sci-fi",
                        "price": 14.99
                    }
                ],
                "pagination": {
                    "page": 1, "limit": 20, "total": 1, "totalPages": 1
                }
            }

+ Response 400 (application/json)

    + Body

            { "code": "INVALID_PARAM", "message": "'genre' phải là một trong: ..." }
```

Cùng thông tin đó, nhưng đọc như văn bản thay vì code.

### Tooling demo

```bash
# Render HTML với live reload
aglio -i 1_APIBlueprint/book-api.apib -s

# Build static HTML
aglio -i 1_APIBlueprint/book-api.apib -o docs.html

# Mock server
drakov -f 1_APIBlueprint/book-api.apib -p 3000
curl http://localhost:3000/v1/books
```

##  — RAML 1.0: API design-first có cấu trúc

### Tóm tắt

RAML viết bằng YAML thuần. RAML có ửu điểm ở khả năng tái sử dụng thông qua `traits` và `resourceTypes`.

### Điểm mạnh

**Tái sử dụng** Đây là ưu điểm của RAML. Thay vì định nghĩa lại pagination parameters ở mỗi endpoint, định nghĩa một lần và áp dụng với `is: [paginated]`. Tương tự với authentication, error responses.

**Resource Types — template cho endpoint:** Có thể tạo template cho nhóm endpoint CRUD, áp dụng cho nhiều resource.

### Điểm yếu

**Ecosystem gắn với MuleSoft:** Tooling tốt nhất đều thuộc hệ sinh thái MuleSoft. Ngoài đó, lựa chọn khá hạn chế.

### Ví dụ

```yaml
#%RAML 1.0
title: Book Management API
version: v1
baseUri: http://localhost:5000/{version}
mediaType: application/json

types:
  Genre:
    type: string
    enum: [fiction, non-fiction, sci-fi, history, biography]

  Book:
    type: object
    properties:
      id:
        type: integer
        required: false    # readonly — server gán
      title: string
      author: string
      genre: Genre         # ← tái sử dụng type đã định nghĩa
      isbn:
        type: string | nil
        required: false
      price:
        type: number | nil
        required: false

# ── TRAITS: định nghĩa một lần, dùng nhiều nơi ──────────────────
traits:
  paginated:
    queryParameters:
      page:
        type: integer
        default: 1
        minimum: 1
        required: false
      limit:
        type: integer
        default: 20
        minimum: 1
        maximum: 100
        required: false
    responses:
      400:
        body:
          type: ErrorResponse

  hasNotFound:
    responses:
      404:
        description: Không tìm thấy sách với ID đã cho
        body:
          type: ErrorResponse
          example:
            code: BOOK_NOT_FOUND
            message: Cannot find book with this id

# ── ENDPOINTS: gọn vì dùng traits ────────────────────────────────
/books:
  get:
    is: [paginated]        # ← pagination params + 400 response tự động có
    queryParameters:
      genre:
        type: Genre
        required: false
      q:
        type: string
        required: false
    responses:
      200:
        body:
          type: object
          properties:
            data: Book[]
            pagination: Pagination

  post:
    body:
      type: CreateBookRequest
    responses:
      201:
        body:
          type: Book

  /{book_id}:
    get:
      is: [hasNotFound]    # ← 404 response tự động có
      responses:
        200:
          body:
            type: Book

    put:
      is: [hasNotFound]
      body:
        type: UpdateBookRequest
      responses:
        200:
          body:
            type: Book

    delete:
      is: [hasNotFound]
      responses:
        204:
          description: Xóa thành công
```

**So sánh với OpenAPI:** Cùng logic 404 phải lặp lại ở GET/PUT/DELETE. OpenAPI dùng `$ref` cho response schema — nhưng vẫn phải khai báo `responses.404` ở mỗi endpoint. RAML với `is: [hasNotFound]` gọn hơn hẳn.

### Tooling demo

```bash
# Render HTML documentation
raml2html 2_RAML/book-api.raml > docs.html
open docs.html

# Mock server
osprey-mock-service -f 2_RAML/book-api.raml -p 8000
curl http://localhost:8000/v1/books

```

---

##  — TypeSpec: API documentation như viết code

### Tóm tắt

TypeSpec là một **DSL (Domain Specific Language)** có cú pháp gần với TypeScript. TypeSpec không phải output mà là nó là input mà để compile ra OpenAPI, JSON Schema, Protobuf,...

### Điểm mạnh

**Type safety tại compile time:** Nếu bạn tham chiếu một type chưa định nghĩa, dùng decorator sai, hay có lỗi trong spec — TypeSpec báo lỗi ngay lúc chạy `tsp compile`.

**Generics thực sự:** `PagedResponse<T>` là generics thực sự — như TypeScript. Một lần định nghĩa, dùng cho mọi list endpoint.

```typescript
model PagedResponse<T> {
  data: T[];
  pagination: Pagination;
}
// Sử dụng: PagedResponse<Book>, PagedResponse<Member>, ...
// Mỗi cái sinh ra một schema riêng trong OpenAPI output
```

### Điểm yếu

**Ecosystem còn non trẻ:** Ra mắt 2022, nhiều tool chưa hỗ trợ `.tsp` trực tiếp.

**Chưa có nhiều tài nguyên**

### Ví dụ — Book model và GET /v1/books

```typescript
import "@typespec/http";
import "@typespec/rest";
using TypeSpec.Http;

@service({ title: "Book Management API", version: "1.0.0" })
@server("http://localhost:5000", "Local")
namespace BookManagementAPI;

// Enum — type-safe, compiler bắt lỗi nếu dùng sai giá trị
enum Genre {
  Fiction: "fiction",
  NonFiction: "non-fiction",
  SciFi: "sci-fi",
  History: "history",
  Biography: "biography",
}

// Model với decorators inline — ngắn gọn hơn YAML nhiều
model Book {
  @visibility("read") id: int32;    // readonly: không xuất hiện trong request body
  title: string;
  author: string;
  isbn?: string | null;
  genre: Genre;                     // compile error nếu gán giá trị ngoài enum
  publishedYear?: int32 | null;
  price?: float64 | null;
}

// Generic — định nghĩa một lần, dùng cho mọi list endpoint
model PagedResponse<T> {
  data: T[];
  pagination: Pagination;
}

model Pagination {
  page: int32;
  limit: int32;
  total: int32;
  totalPages: int32;
}

@error
model ApiError {
  code: string;
  message: string;
}

// Spread để tái sử dụng query params
model PaginationParams {
  @query page?: int32 = 1;
  @query limit?: int32 = 20;
}

// Endpoints — tổ chức theo namespace
@route("/v1/books")
@tag("books")
namespace Books {

  @get
  op list(
    ...PaginationParams,             // spread pagination params
    @query genre?: Genre,
    @query q?: string,
  ): {
    @statusCode statusCode: 200;
    @body body: PagedResponse<Book>; // generic type
  } | {
    @statusCode statusCode: 400;
    @body body: ApiError;
  };

  @post
  op create(@body body: CreateBookRequest): {
    @statusCode statusCode: 201;
    @body book: Book;
  } | {
    @statusCode statusCode: 400;
    @body body: ApiError;
  };

  @route("/{bookId}")
  namespace ById {
    @get
    op get(@path bookId: string): Book | { @statusCode statusCode: 404; @body body: ApiError; };

    @put
    op update(@path bookId: string, @body body: UpdateBookRequest): Book
      | { @statusCode statusCode: 404; @body body: ApiError; };

    @delete
    op delete(@path bookId: string): { @statusCode statusCode: 204; }
      | { @statusCode statusCode: 404; @body body: ApiError; };
  }
}
```

### Tooling demo

```bash

# Tạo tspconfig.yaml
cat > tspconfig.yaml << 'EOF'
emit:
  - "@typespec/openapi3"
options:
  "@typespec/openapi3":
    output-file: "openapi.yaml"
EOF

# Compile .tsp → openapi.yaml
tsp compile 3_TypeSpec/book-api.tsp

# Dùng tool OpenAPI
redocly preview-docs openapi.yaml
prism mock openapi.yaml
```
