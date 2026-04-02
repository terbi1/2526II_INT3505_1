from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask import request, jsonify

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
db = SQLAlchemy(app)

class Author(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    # Mối quan hệ 1-N: Trỏ tới bảng Book
    books = db.relationship('Book', backref='author',  lazy=True)
 
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default='available')
    author_id = db.Column(db.Integer, db.ForeignKey('author.id'), nullable=False)

@app.route('/api/v1/books', methods=['GET'])
def get_books():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    search_query = request.args.get('q', type=str)

    query = Book.query
    if search_query:
        query = query.filter(Book.title.ilike(f'%{search_query}%'))

    pagination = query.paginate(page=page, per_page=limit, error_out=False)

    data = []
    for book in pagination.items:
        data.append({
            'id': book.id,
            'title': book.title,
            'author_id': book.author_id,
            'status': book.status
        })

    return jsonify({
        'data': data,
        'meta': {
            'pagination': {
                'total_records': pagination.total,
                'current_page': pagination.page,
                'total_pages': pagination.pages,
                'next_page': pagination.next_num,
                'prev_page': pagination.prev_num
            }
        }
    })

# offset
@app.route('/api/v2/books', methods=['GET'])
def get_books_offset():
    offset = request.args.get('offset', default=0, type=int)
    limit = request.args.get('limit', default=20, type=int)

    query = Book.query

    books = query.offset(offset).limit(limit).all()

    total_records = query.count()

    data = []
    for book in books:
        data.append({
            'id': book.id,
            'title': book.title,
            'author_id': book.author_id,
            'status': book.status
        })

    return jsonify({
        'data': data,
        'meta': {
            'pagination': {
                'offset': offset,
                'limit': limit,
                'total_records': total_records,
                'has_more': (offset + limit) < total_records
            }
        }
    })

# cursor based
@app.route('/api/v3/books', methods=['GET'])
def get_books_cursor():
    limit = request.args.get('limit', 20, type=int)
    cursor = request.args.get('cursor', default=0, type=int) 

    query = Book.query

    if cursor > 0:
        query = query.filter(Book.id > cursor)

    books = query.order_by(Book.id.asc()).limit(limit + 1).all()

    has_next = len(books) > limit
    next_cursor = None
    
    if has_next:
        books.pop() 
        next_cursor = books[-1].id

    data = []
    for book in books:
        data.append({
            'id': book.id,
            'title': book.title,
            'author_id': book.author_id,
            'status': book.status
        })

    return jsonify({
        'data': data,
        'meta': {
            'pagination': {
                'next_cursor': next_cursor,
                'has_next': has_next,
                'limit': limit
            }
        }
    })