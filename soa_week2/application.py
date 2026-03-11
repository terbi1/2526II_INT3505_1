from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

API_KEY = "123456"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data.db"
db = SQLAlchemy(app)
app.app_context().push()

class Drink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(120))

    def __repr__(self):
        return f"{self.name} - {self.description}"

@app.route('/')
def index():
    return "hello"

@app.route('/v1/drinks', methods=['GET'])
def get_drinks():

    drinks = Drink.query.all()

    output = []

    for drink in drinks:
        drink_data = {'name':drink.name, "description": drink.description}

        output.append(drink_data)

    return jsonify(output)

@app.route('/v2/drinks', methods=['GET'])
def get_drinks_v2():
    api_key = request.headers.get("x-api-key")
    if(api_key == API_KEY):
        drinks = Drink.query.all()

        output = []

        for drink in drinks:
            drink_data = {'name':drink.name, "description": drink.description}

            output.append(drink_data)

        return jsonify(output)
    
    return {"msg": "Invalid key. GET OUT!"}, 401
