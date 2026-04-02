from datetime import datetime, timedelta
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask import request, jsonify

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
db = SQLAlchemy(app)

class Author(db.Model):
    __tablename__ = "author"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    books = db.relationship('Book', backref='author',  lazy=True)
 
class Book(db.Model):
    __tablename__ = "book"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default='available')
    author_id = db.Column(db.Integer, db.ForeignKey('author.id'), nullable=False)
    transactions = db.relationship('Transaction', backref='book', lazy=True)

class User(db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    
    transactions = db.relationship('Transaction', backref='user', lazy=True)

class Transaction(db.Model):
    __tablename__ = "transaction"
    id = db.Column(db.Integer, primary_key=True)
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    
    borrow_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    due_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    return_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    status = db.Column(db.String(20), default='borrowed') # borrowed, returned, overdue

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
                'total_pages': pagination.pages
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
                'limit': limit,
                'next': f"/api/v3/books?cursor={next_cursor}&limit={limit}"
            }
        }
    })

@app.route('/api/v1/books', methods=['POST'])
def create_book():
    body = request.get_json()
    
    # Basic validation
    if not body or not body.get('title') or not body.get('author_id'):
        return jsonify({'error': 'Missing title or author_id'}), 400
        
    author = Author.query.get(body['author_id'])
    if not author:
        return jsonify({'error': 'Author not found'}), 404

    new_book = Book(title=body['title'], author_id=body['author_id'])
    db.session.add(new_book)
    db.session.commit()
    
    return jsonify({'message': 'Book created successfully', 'book_id': new_book.id}), 201

# [POST] Borrow a Book (Create Transaction)
@app.route('/api/v1/transactions', methods=['POST'])
def borrow_book():
    body = request.get_json()
    user_id = body.get('user_id')
    book_id = body.get('book_id')
    
    book = Book.query.get(book_id)
    user = User.query.get(user_id)
    
    if not book or not user:
        return jsonify({'error': 'User or Book not found'}), 404
        
    if book.status != 'available':
        return jsonify({'error': 'Book is currently not available'}), 400

    # Create transaction and update book status
    due_date = datetime.utcnow() + timedelta(days=14) # 14-day borrowing period
    new_transaction = Transaction(
        user_id=user_id, 
        book_id=book_id, 
        due_date=due_date, 
        status='borrowed'
    )
    
    book.status = 'borrowed'
    
    db.session.add(new_transaction)
    db.session.commit()
    
    return jsonify({
        'message': 'Book borrowed successfully', 
        'transaction_id': new_transaction.id,
        'due_date': due_date.isoformat()
    }), 201

# [PATCH] Return a Book (Update Transaction)
@app.route('/api/v1/transactions/<int:transaction_id>', methods=['PATCH'])
def return_book(transaction_id):
    transaction = Transaction.query.get(transaction_id)
    
    if not transaction:
        return jsonify({'error': 'Transaction not found'}), 404
        
    if transaction.status == 'returned':
        return jsonify({'error': 'Book is already returned'}), 400

    # Update transaction and book status
    transaction.status = 'returned'
    transaction.return_date = datetime.utcnow()
    
    book = Book.query.get(transaction.book_id)
    book.status = 'available'
    
    db.session.commit()
    
    return jsonify({'message': 'Book returned successfully'}), 200

# [GET] Nested Resource: Get all transactions for a specific user
@app.route('/api/v1/users/<int:user_id>/transactions', methods=['GET'])
def get_user_transactions(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    data = [{
        'transaction_id': t.id,
        'book_title': t.book.title,
        'borrow_date': t.borrow_date.isoformat(),
        'due_date': t.due_date.isoformat(),
        'return_date': t.return_date.isoformat() if t.return_date else None,
        'status': t.status
    } for t in user.transactions] # Using the backref relationship!
    
    return jsonify({'user': user.name, 'transactions': data}), 200

@app.route('/api/v1/transactions/<int:transaction_id>', methods=['GET'])
def get_transaction(transaction_id):
    
    transaction = Transaction.query.get(transaction_id)

    data = [{
        'transaction_id': transaction.id,
        'book_title': transaction.book.title,
        'borrow_date': transaction.borrow_date.isoformat(),
        'due_date': transaction.due_date.isoformat(),
        'return_date': transaction.return_date.isoformat() if transaction.return_date else None,
        'status': transaction.status
    }] # Using the backref relationship!
    
    return jsonify(data), 200

@app.route('/api/v1/transactions', methods=['GET'])
def get_transactions():
    
    transactions = Transaction.query.all()

    data = [{
        'transaction_id': t.id,
        'book_title': t.book.title,
        'borrow_date': t.borrow_date.isoformat(),
        'due_date': t.due_date.isoformat(),
        'return_date': t.return_date.isoformat() if t.return_date else None,
        'status': t.status
    } for t in transactions] # Using the backref relationship!
    
    return jsonify({'transactions': data}), 200

# [GET] Get all users
@app.route('/api/v1/users', methods=['GET'])
def get_all_users():
    # Fetch all users from the database
    users = User.query.all()
    
    # Format the data into a list of dictionaries
    data = []
    for user in users:
        data.append({
            'id': user.id,
            'name': user.name,
            'email': user.email
        })
        
    return jsonify({
        'data': data,
        'meta': {
            'total_users': len(data)
        }
    }), 200

# [GET] Get a specific user by ID
@app.route('/api/v1/users/<int:user_id>', methods=['GET'])
def get_user_by_id(user_id):
    # .get() will automatically search by Primary Key (id)
    user = User.query.get(user_id)
    
    # Handle the case where the user doesn't exist
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    return jsonify({
        'data': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            # We can easily count their transactions thanks to the db.relationship!
            'total_transactions': len(user.transactions) 
        }
    }), 200

# [GET] Lấy danh sách tất cả tác giả
@app.route('/api/v1/authors', methods=['GET'])
def get_all_authors():
    authors = Author.query.all()
    
    data = []
    for author in authors:
        data.append({
            'id': author.id,
            'name': author.name,
            # Tận dụng relationship để đếm số sách tác giả này có trong hệ thống
            'total_books': len(author.books) 
        })
        
    return jsonify({
        'data': data,
        'meta': {
            'total_authors': len(data)
        }
    }), 200

# [GET] Lấy thông tin chi tiết của một tác giả theo ID
@app.route('/api/v1/authors/<int:author_id>', methods=['GET'])
def get_author_by_id(author_id):
    author = Author.query.get(author_id)
    
    # Kiểm tra nếu ID không tồn tại
    if not author:
        return jsonify({'error': 'Author not found'}), 404
        
    return jsonify({
        'data': {
            'id': author.id,
            'name': author.name,
            'total_books': len(author.books)         
        }
    }), 200