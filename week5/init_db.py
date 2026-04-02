from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import random

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class Author(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    books = db.relationship('Book', backref='author', lazy=True)

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default='available')
    author_id = db.Column(db.Integer, db.ForeignKey('author.id'), nullable=False)

class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    join_date = db.Column(db.DateTime, default=datetime.utcnow)
    loans = db.relationship('Loan', backref='member', lazy=True)

class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    borrow_date = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=False)
    return_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='borrowed') # borrowed, returned, overdue


def seed_database():
    with app.app_context():
        db.drop_all()
        db.create_all()

        authors = [
            Author(name="Robert C. Martin"),
            Author(name="Martin Fowler"),
            Author(name="Erich Gamma"),
            Author(name="Linus Torvalds"),
            Author(name="Alan Turing")
        ]
        db.session.add_all(authors)
        db.session.commit()

        books = []
        for i in range(1, 51):
            random_author = random.choice(authors)
            book = Book(
                title=f"Lập trình nâng cao - Tập {i}",
                status="available",
                author_id=random_author.id
            )
            books.append(book)
        db.session.add_all(books)
        db.session.commit()

        member = Member(name="Nguyễn Văn A", email="vana@example.com")
        db.session.add(member)
        db.session.commit()

        print("✅ Đã tạo cơ sở dữ liệu 'library.db' và thêm dữ liệu mẫu thành công!")
        print(f"Tổng số sách hiện có: {Book.query.count()} cuốn.")

if __name__ == '__main__':
    seed_database()