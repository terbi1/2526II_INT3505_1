from flask import Flask, jsonify, request
from datetime import datetime, timezone

app = Flask(__name__)

books = [
    {"id": 1, "title": "The Great Gatsby", "author": "F. Scott Fitzgerald"},
    {"id": 2, "title": "1984", "author": "George Orwell"}
]
reviews = [
    {"id": 1, "book_id": 1, "comment": "A classic!"},
    {"id": 2, "book_id": 2, "comment": "Mind-bending."}
]

def error(status_code, error_code, message, link=None):
    error_payload = {
        "error": {
            "code": error_code,
            "message": message
        }
    }
    if link:
        error_payload["error"]["link"] = link
        
    return jsonify(error_payload), status_code

# Global Error Handlers (Ensures HTML is never returned on bad URLs)
@app.errorhandler(404)
def resource_not_found(e):
    return error(404, "ROUTE_NOT_FOUND", "The requested endpoint does not exist.")

@app.errorhandler(405)
def method_not_allowed(e):
    return error(405, "METHOD_NOT_ALLOWED", "This HTTP method is not allowed for this endpoint.")

@app.route("/api/v1/status", methods=['GET'])
def get_status():
    """Casing & Types: Demonstrates strict snake_case and ISO-8601 dates."""
    return jsonify({
        "data": {
            "is_server_online": True, 
            "last_checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        }
    }), 200

@app.route("/api/v1/books", methods=['GET'])
def get_books():
    result = books.copy()

    author_filter = request.args.get('filter[author]')
    if author_filter:
        result = [b for b in result if b['author'].lower() == author_filter.lower()]

    sort_param = request.args.get('sort')
    if sort_param:
        field, direction = sort_param.split(',') if ',' in sort_param else (sort_param, 'asc')
        result.sort(key=lambda x: x.get(field, ''), reverse=(direction == 'desc'))

    limit = request.args.get('limit', default=10, type=int)
    offset = request.args.get('offset', default=0, type=int)
    paginated_result = result[offset : offset + limit]

    fields_param = request.args.get('fields')
    if fields_param:
        fields = fields_param.split(',')
        paginated_result = [{k: v for k, v in b.items() if k in fields} for b in paginated_result]

    return jsonify({
        "data": paginated_result,
        "meta": {
            "total": len(result),
            "limit": limit,
            "offset": offset
        }
    }), 200

@app.route("/api/v1/books", methods=['POST'])
def add_book():
    data = request.json
    
    if not data or not data.get('title'):
        return jsonify({"error":{
            "error_code": "MISSING_FIELD", 
            "message":"Title is required."}})
    
    if any(b['title'].lower() == data['title'].lower() for b in books):
        return error(409, "DUPLICATE_BOOK", "Book already added.")
        
    new_book = {
        "id": len(books) + 1,
        "title": data['title'],
        "author": data.get('author', 'Unknown'),
    }
    books.append(new_book)
    
    return jsonify({"data": new_book, "message": "Book successfully added"}), 201

@app.route("/api/v1/books/<int:id>", methods=['GET', 'PUT', 'PATCH', 'DELETE'])
def manage_single_book(id):
    book = next((b for b in books if b['id'] == id), None)
    
    if not book:
        return error(404, "BOOK_NOT_FOUND", "Book not found")

    if request.method == 'GET':
        return jsonify({"data": book}), 200
        
    elif request.method == 'PUT':
        data = request.json
        if not data or not data.get('title') or not data.get('author'):
            return error(400, "MISSING_FIELDS", "PUT requires all fields (title, author).")
        book['title'] = data['title']
        book['author'] = data['author']
        return jsonify({"data": book}), 200
        
    elif request.method == 'PATCH':
        data = request.json
        if 'title' in data: book['title'] = data['title']
        if 'author' in data: book['author'] = data['author']
        return jsonify({"data": book}), 200
        
    elif request.method == 'DELETE':
        books.remove(book)
        return '', 204

@app.route("/api/v1/books/<int:id>/reviews", methods=['GET'])
def get_book_reviews(id):
    book_reviews = [r for r in reviews if r['book_id'] == id]
    return jsonify({"data": book_reviews}), 200

@app.route("/api/v1/books/<int:id>/reviews/<int:review_id>/comment", methods=['GET'])
def get_specific_review_comment(id, review_id):
    review = next((r for r in reviews if r['id'] == review_id and r['book_id'] == id), None)

    return jsonify({
        "data": {
            "comment": review['comment']
        }
    }), 200

@app.route("/api/v2/books", methods=['GET'])
def get_books_v2():
    return jsonify({
        "data": books,
        "message": "New version"
    }), 200