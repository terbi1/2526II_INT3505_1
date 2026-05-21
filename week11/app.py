from flask import Flask
from routes.crud_routes import crud_bp
from routes.query_routes import query_bp
from routes.hateoas_routes import hateoas_bp
from routes.event_routes import event_bp
from routes.webhook_routes import webhook_bp
from routes.notification_routes import notification_bp

app = Flask(__name__)
app.config['SECRET_KEY'] = 'api-patterns-demo-2024'

app.register_blueprint(crud_bp,         url_prefix='/api/v1/products')
app.register_blueprint(query_bp,        url_prefix='/api/v1/search')
app.register_blueprint(hateoas_bp,      url_prefix='/api/v1/orders')
app.register_blueprint(event_bp,        url_prefix='/api/v1/events')
app.register_blueprint(webhook_bp,      url_prefix='/api/v1/webhooks')
app.register_blueprint(notification_bp, url_prefix='/api/v1/notifications')


@app.route('/')
def index():
    return {
        "service": "API Design Patterns Demo",
        "patterns": {
            "1_CRUD":         "/api/v1/products",
            "2_Query":        "/api/v1/search/products",
            "3_HATEOAS":      "/api/v1/orders",
            "4_Event_driven": "/api/v1/events",
            "5_Webhook":      "/api/v1/webhooks",
            "6_Notification": "/api/v1/notifications",
        },
        "docs": ""
    }

if __name__ == '__main__':
    app.run(debug=True, port=5000)
