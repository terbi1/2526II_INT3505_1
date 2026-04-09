import random
from datetime import datetime, timedelta
import time
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import insert

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
def seed_database_massive(total_records=10_000_000, batch_size=50_000):
    with app.app_context():
        print("--- Bắt đầu quá trình Seeding quy mô lớn ---")
        db.drop_all()
        db.create_all()

        # 1. Tối ưu hóa SQLite để ghi thần tốc
        db.session.execute(db.text("PRAGMA synchronous = OFF"))
        db.session.execute(db.text("PRAGMA journal_mode = WAL"))

        # 2. Tạo dữ liệu gốc (Authors & Users)
        authors = [Author(name=f"Author {i}") for i in range(1, 1001)]
        users = [User(name=f"User {i}", email=f"user{i}@test.com") for i in range(1, 10001)]
        db.session.add_all(authors + users)
        db.session.commit()
        
        author_ids = [a.id for a in authors]
        user_ids = [u.id for u in users]

        # 3. Seeding 10 triệu Books bằng phương pháp Batching
        print(f"Đang tạo {total_records} bản ghi Book...")
        start_time = time.time()
        
        for i in range(0, total_records, batch_size):
            batch = []
            for j in range(i, min(i + batch_size, total_records)):
                batch.append({
                    "title": f"Book Title {j}",
                    "status": "available",
                    "author_id": random.choice(author_ids)
                })
            
            # Sử dụng Bulk Insert (Insert trực tiếp Dictionary để bỏ qua overhead của Model)
            db.session.execute(insert(Book), batch)
            
            # Commit theo từng đợt để giải phóng RAM
            if (i + batch_size) % (batch_size * 10) == 0:
                db.session.commit()
                elapsed = time.time() - start_time
                print(f"Đã xong: {i + batch_size:,} / {total_records:,} bản ghi ({elapsed:.2f}s)")

        db.session.commit()
        
        total_time = time.time() - start_time
        print(f"✅ Hoàn thành! Tổng thời gian: {total_time/60:.2f} phút")

if __name__ == '__main__':
    seed_database_massive()