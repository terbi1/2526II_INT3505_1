import math
from flasgger import Swagger

from flask import Flask, jsonify, request, abort

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False
app.config['SWAGGER'] = {
    'title': 'Drinks API',
    'uiversion': 3,
    'openapi': '3.0.0'
}

swagger = Swagger(app, template_file='openapi.yaml')

VALID_GENRES = {"fiction", "non-fiction", "sci-fi", "history", "biography"}

BOOKS = [{"id": 1,"title": "Dune", "author": "Frank Herbert", "isbn": "978-0-441-01359-8",
         "genre": "sci-fi", "publishedYear": 1965, "price": 14.99},
        {"id": 2,"title": "Sapiens", "author": "Yuval Noah Harari", "isbn": "978-0-06-231609-7",
         "genre": "history", "publishedYear": 2011, "price": 18.99},
        {"id": 3,"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "isbn": "978-0-7432-7356-5",
         "genre": "fiction", "publishedYear": 1925, "price": 12.99},
        {"id": 4,"title": "Clean Code", "author": "Robert C. Martin", "isbn": "978-0-13-235088-4",
         "genre": "non-fiction", "publishedYear": 2008, "price": 35.99},
        {"id": 5,"title": "Ender's Game", "author": "Orson Scott Card", "isbn": "978-0-8125-5070-6",
         "genre": "sci-fi", "publishedYear": 1985, "price": 11.99}]

def make_error(code: str, message: str, status: int = 400):
    body = {"code": code, "message": message}
    return jsonify(body), status


def paginate(items: list, page: int, limit: int) -> tuple[list, dict]:
    total = len(items)
    total_pages = max(1, math.ceil(total / limit))
    start = (page - 1) * limit
    end = start + limit
    return items[start:end], {
        "page": page,
        "limit": limit,
        "total": total,
        "totalPages": total_pages,
    }

@app.get("/v1/books")
def list_books():
    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        return make_error("INVALID_PARAM", "Page must be an integer")

    try:
        limit = min(100, max(1, int(request.args.get("limit", 20))))
    except ValueError:
        return make_error("INVALID_PARAM", "Limit must be an integer")

    genre = request.args.get("genre")
    if genre and genre not in VALID_GENRES:
        return make_error("INVALID_PARAM",
                          f"'genre' phải là một trong: {', '.join(sorted(VALID_GENRES))}.")

    q = (request.args.get("q") or "").strip().lower()

    books = BOOKS

    if genre:
        books = [b for b in books if b.get("genre") == genre]

    if q:
        books = [
            b for b in books
            if q in b.get("title", "").lower() or q in b.get("author", "").lower()
        ]

    page_data, pagination = paginate(books, page, limit)

    return jsonify({"data": page_data, "pagination": pagination}), 200


@app.post("/v1/books")
def create_book():
    """POST /v1/books — Create a new book."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return make_error("BAD_REQUEST", "Request body must be JSON")

    book_id = len(BOOKS) + 1
    book = {
        "id": book_id,
        "title": data["title"],
        "author": data["author"],
        "isbn": data.get("isbn"),
        "genre": data["genre"],
        "publishedYear": data.get("publishedYear"),
        "price": data.get("price")
    }
    BOOKS[book_id] = book
    return jsonify(book), 201


@app.get("/v1/books/<book_id>")
def get_book(book_id: str):
    book = BOOKS.get(book_id)
    if not book:
        return make_error("BOOK_NOT_FOUND", "Cannot find book with this id", status=404)
    return jsonify(book), 200


@app.put("/v1/books/<book_id>")
def update_book(book_id: str):
    """PUT /v1/books/<id> — Replace book data."""
    book = BOOKS.get(book_id)
    if not book:
        return make_error("BOOK_NOT_FOUND", "Cannot find book with this id", status=404)

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return make_error("BAD_REQUEST", "Request body must be JSON")

    book.update({
        "title": data["title"],
        "author": data["author"],
        "isbn": data.get("isbn", book.get("isbn")),
        "genre": data["genre"],
        "publishedYear": data.get("publishedYear", book.get("publishedYear")),
        "price": data.get("price", book.get("price")),
    })
    return jsonify(book), 200


@app.delete("/v1/books/<book_id>")
def delete_book(book_id: str):
    if book_id not in BOOKS:
        return make_error("BOOK_NOT_FOUND", "Cannot find book with this id", status=404)
    del BOOKS[book_id]
    return "", 204  

@app.errorhandler(404)
def not_found(_e):
    return make_error("NOT_FOUND", "", status=404)


@app.errorhandler(405)
def method_not_allowed(_e):
    return make_error("METHOD_NOT_ALLOWED", "", status=405)


@app.errorhandler(500)
def internal_error(_e):
    return make_error("INTERNAL_ERROR", "", status=500)