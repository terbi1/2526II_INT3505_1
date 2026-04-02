import random
from datetime import datetime, timedelta
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# 1. Initialize Flask App and Database Config
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# 2. Define the Models
class Author(db.Model):
    __tablename__ = 'author'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    books = db.relationship('Book', backref='author', lazy=True)

class Book(db.Model):
    __tablename__ = 'book'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default='available') # available, borrowed, lost
    author_id = db.Column(db.Integer, db.ForeignKey('author.id'), nullable=False)
    transactions = db.relationship('Transaction', backref='book', lazy=True)

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    transactions = db.relationship('Transaction', backref='user', lazy=True)

class Transaction(db.Model):
    __tablename__ = 'transaction'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    borrow_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    due_date = db.Column(db.DateTime, nullable=False) 
    return_date = db.Column(db.DateTime, nullable=True) 
    status = db.Column(db.String(20), default='borrowed') 

# 3. Seeding Function
def seed_database():
    with app.app_context():
        print("Dropping old tables...")
        db.drop_all()
        
        print("Creating new tables...")
        db.create_all()

        print("Seeding Authors...")
        authors = [
            Author(name="George Orwell"),
            Author(name="J.K. Rowling"),
            Author(name="J.R.R. Tolkien"),
            Author(name="Agatha Christie")
        ]
        db.session.add_all(authors)
        db.session.commit()

        print("Seeding Users...")
        users = [
            User(name="Alice Smith", email="alice@example.com"),
            User(name="Bob Johnson", email="bob@example.com"),
            User(name="Charlie Brown", email="charlie@example.com")
        ]
        db.session.add_all(users)
        db.session.commit()

        print("Seeding Books...")
        books = []
        # Create 50 mock books to help test pagination
        for i in range(1, 51):
            random_author = random.choice(authors)
            book = Book(
                title=f"Sample Book Title {i}",
                status="available",
                author_id=random_author.id
            )
            books.append(book)
        db.session.add_all(books)
        db.session.commit()

        print("Seeding Transactions...")
        # Simulate Alice borrowing Book #1 (currently borrowed)
        t1 = Transaction(
            user_id=users[0].id,
            book_id=books[0].id,
            borrow_date=datetime.utcnow() - timedelta(days=5),
            due_date=datetime.utcnow() + timedelta(days=9),
            status="borrowed"
        )
        books[0].status = "borrowed" # Update book status

        # Simulate Bob borrowing Book #2 and returning it early
        t2 = Transaction(
            user_id=users[1].id,
            book_id=books[1].id,
            borrow_date=datetime.utcnow() - timedelta(days=20),
            due_date=datetime.utcnow() - timedelta(days=6),
            return_date=datetime.utcnow() - timedelta(days=10),
            status="returned"
        )
        
        db.session.add_all([t1, t2])
        db.session.commit()

        print(f"✅ Database initialized successfully!")
        print(f"-> Created {Author.query.count()} Authors")
        print(f"-> Created {User.query.count()} Users")
        print(f"-> Created {Book.query.count()} Books")
        print(f"-> Created {Transaction.query.count()} Transactions")

if __name__ == '__main__':
    seed_database()