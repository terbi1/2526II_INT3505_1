from flask import Flask, request, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache

from random import randint

app = Flask(__name__)
app.config['CACHE_TYPE'] = 'simple'
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data.db"
cache = Cache(app)

API_KEY = "123456"

db = SQLAlchemy(app)
app.app_context().push()

class Drink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(120))

    def __repr__(self):
        return f"{self.name} - {self.description}"

@app.route('/')
@cache.cached(timeout=10) #server side cache - not restful
def index():
    randnum = randint (1,1000)
    res = make_response(jsonify({"lucky-number": randnum}))
    res.headers['Cache-Control'] = 'public, max-age=10' #client side cache
    return res

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
