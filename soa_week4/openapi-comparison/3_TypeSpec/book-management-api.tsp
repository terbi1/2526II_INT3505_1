import "@typespec/http";
import "@typespec/rest";
import "@typespec/openapi3";

using TypeSpec.Http;
using TypeSpec.Rest;

/**
 * Book Management API
 *
 * API quản lý sách đơn giản viết bằng Flask.
 * Hỗ trợ tìm kiếm, lọc theo thể loại, phân trang và CRUD.
 *
 * Nguồn: app.py (Flask + Flasgger)
 * In-memory store — dữ liệu reset khi restart server.
 * Không có authentication.
 */
@service({
  title: "Book Management API",
  version: "1.0.0",
})
@server("http://localhost:5000", "Local development")
namespace BookManagementAPI;

// ─────────────────────────────────────────────
// ENUMS
// ─────────────────────────────────────────────

/**
 * Thể loại sách hợp lệ.
 * Tương ứng với VALID_GENRES = {"fiction", "non-fiction", "sci-fi", "history", "biography"}
 * trong app.py. GET /v1/books trả về 400 nếu genre không thuộc tập này.
 */
enum Genre {
  Fiction: "fiction",
  NonFiction: "non-fiction",
  SciFi: "sci-fi",
  History: "history",
  Biography: "biography",
}

// ─────────────────────────────────────────────
// MODELS
// ─────────────────────────────────────────────

/** Một cuốn sách trong hệ thống. */
model Book {
  /**
   * ID tự tăng, do server gán: len(BOOKS) + 1.
   * Readonly — không truyền khi tạo/cập nhật.
   */
  @visibility("read")
  id: int32;

  title: string;
  author: string;

  /** Có thể null nếu không cung cấp khi tạo. */
  isbn?: string | null;

  genre: Genre;

  /** Năm xuất bản. Có thể null. */
  publishedYear?: int32 | null;

  /** Giá sách. Có thể null. */
  price?: float64 | null;
}

/**
 * Body để tạo sách mới (POST /v1/books).
 *
 * QUAN TRỌNG: `title`, `author`, `genre` là bắt buộc theo logic app.py
 * (truy cập trực tiếp data["title"] v.v.). Thiếu các field này sẽ gây
 * KeyError → HTTP 500 vì không có validation tại tầng app.
 */
model CreateBookRequest {
  title: string;
  author: string;
  isbn?: string;
  genre: Genre;
  publishedYear?: int32;
  price?: float64;
}

/**
 * Body để cập nhật sách (PUT /v1/books/{book_id}).
 *
 * PUT thay thế toàn bộ — `title`, `author`, `genre` bắt buộc.
 * `isbn`, `publishedYear`, `price` optional: server giữ nguyên
 * giá trị cũ nếu không truyền (data.get("isbn", book.get("isbn"))).
 */
model UpdateBookRequest {
  title: string;
  author: string;

  /** Nếu bỏ qua, giữ giá trị cũ của sách. */
  isbn?: string;

  genre: Genre;

  /** Nếu bỏ qua, giữ giá trị cũ của sách. */
  publishedYear?: int32;

  /** Nếu bỏ qua, giữ giá trị cũ của sách. */
  price?: float64;
}

/** Metadata phân trang trả về cùng BookListResponse. */
model Pagination {
  /** Trang hiện tại (input page sau khi clamp: max(1, page)). */
  page: int32;

  /** Số bản ghi/trang (input limit sau khi clamp vào [1, 100]). */
  limit: int32;

  /** Tổng số sách sau khi áp dụng filter genre và q. */
  total: int32;

  /** max(1, ceil(total / limit)) */
  totalPages: int32;
}

/** Response của GET /v1/books. */
model BookListResponse {
  data: Book[];
  pagination: Pagination;
}

/**
 * Cấu trúc lỗi chuẩn từ hàm make_error() trong app.py.
 *
 * Các error handler 404/405/500 trả về message rỗng "".
 * Các lỗi business logic có message mô tả cụ thể.
 */
@error
model ApiError {
  /**
   * Mã lỗi định danh. Các giá trị có thể:
   * - INVALID_PARAM: query param sai
   * - BAD_REQUEST: body không phải JSON
   * - BOOK_NOT_FOUND: không tìm thấy sách
   * - NOT_FOUND: route không tồn tại
   * - METHOD_NOT_ALLOWED: method không hỗ trợ
   * - INTERNAL_ERROR: lỗi server
   */
  code: string;

  /** Mô tả lỗi. Có thể là string rỗng với lỗi từ errorhandler. */
  message: string;
}

// ─────────────────────────────────────────────
// QUERY PARAMS
// ─────────────────────────────────────────────

/** Query params phân trang dùng chung. */
model PaginationParams {
  /**
   * Số trang. Clamp bằng max(1, page) — giá trị < 1 tự động thành 1.
   * Non-integer → 400 INVALID_PARAM.
   */
  @query
  page?: int32 = 1;

  /**
   * Số bản ghi/trang. Clamp vào [1, 100].
   * Non-integer → 400 INVALID_PARAM.
   */
  @query
  limit?: int32 = 20;
}

// ─────────────────────────────────────────────
// HEALTH CHECK
// ─────────────────────────────────────────────

/** Root endpoint — không thuộc prefix /v1. */
@route("/")
namespace Root {
  /**
   * Ping endpoint. Trả về chuỗi cố định.
   * Không liên quan đến base path /v1.
   */
  @get
  op ping(): {
    @statusCode statusCode: 200;
    @body body: { msg: string };
  };
}

// ─────────────────────────────────────────────
// BOOKS
// ─────────────────────────────────────────────

@route("/v1/books")
@tag("books")
namespace Books {

  /**
   * Lấy danh sách sách.
   *
   * Thứ tự xử lý filter trong app.py:
   * 1. Validate page, limit (parse int, clamp)
   * 2. Validate genre (nếu có)
   * 3. Filter theo genre (so sánh ==)
   * 4. Filter theo q (substring, case-insensitive, trên title VÀ author)
   * 5. Paginate
   */
  @get
  op list(
    ...PaginationParams,

    /**
     * Lọc chính xác theo thể loại (b["genre"] == genre).
     * Nếu giá trị không thuộc Genre enum → 400 INVALID_PARAM.
     */
    @query genre?: Genre,

    /**
     * Tìm kiếm trong title hoặc author.
     * Strip whitespace, lowercase, substring match.
     * Bỏ trống hoặc bỏ qua = không filter.
     */
    @query q?: string,
  ): {
    @statusCode statusCode: 200;
    @body body: BookListResponse;
  } | {
    /** page/limit không parse được thành int, hoặc genre không hợp lệ. */
    @statusCode statusCode: 400;
    @body body: ApiError;
  };

  /**
   * Tạo sách mới.
   *
   * `id` = `len(BOOKS) + 1` — không an toàn với concurrent requests,
   * nhưng đây là in-memory demo.
   *
   * Thiếu `title`, `author`, hoặc `genre` trong body sẽ raise
   * Python KeyError → HTTP 500 (không có validation ở app layer).
   */
  @post
  op create(@body body: CreateBookRequest): {
    @statusCode statusCode: 201;
    @body book: Book;
  } | {
    /** Body không phải JSON object (get_json(silent=True) trả về None). */
    @statusCode statusCode: 400;
    @body body: ApiError;
  };

  @route("/{bookId}")
  namespace ById {

    /**
     * Lấy thông tin chi tiết một cuốn sách.
     *
     * book_id trong URL là string, app.py dùng BOOKS.get(book_id) —
     * cần truyền đúng kiểu integer ID khi lookup.
     */
    @get
    op get(@path bookId: string): {
      @statusCode statusCode: 200;
      @body body: Book;
    } | {
      @statusCode statusCode: 404;
      @body body: ApiError;
    };

    /**
     * Thay thế toàn bộ dữ liệu sách (PUT semantics).
     *
     * Các field optional trong UpdateBookRequest sẽ fallback về
     * giá trị cũ của sách nếu không có trong body:
     *   isbn       → data.get("isbn", book.get("isbn"))
     *   publishedYear → data.get("publishedYear", book.get("publishedYear"))
     *   price      → data.get("price", book.get("price"))
     */
    @put
    op update(
      @path bookId: string,
      @body body: UpdateBookRequest,
    ): {
      @statusCode statusCode: 200;
      @body body: Book;
    } | {
      @statusCode statusCode: 400;
      @body body: ApiError;
    } | {
      @statusCode statusCode: 404;
      @body body: ApiError;
    };

    /**
     * Xóa sách khỏi in-memory store.
     * Response 204 không có body (trả về empty string "").
     */
    @delete
    op delete(@path bookId: string): {
      @statusCode statusCode: 204;
    } | {
      @statusCode statusCode: 404;
      @body body: ApiError;
    };
  }
}
