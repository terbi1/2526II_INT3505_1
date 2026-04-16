import connexion

def create_app():
    app = connexion.FlaskApp(__name__, specification_dir=".")
    app.add_api("openapi.yaml")
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="localhost", port=5000)