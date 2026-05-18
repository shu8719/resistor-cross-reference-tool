from flask import Flask, render_template

from routes.analyze import analyze_bp
from routes.bulk import bulk_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.jinja_env.variable_start_string = "[["
    app.jinja_env.variable_end_string = "]]"

    @app.route("/")
    def index():
        return render_template("index.html")

    app.register_blueprint(analyze_bp)
    app.register_blueprint(bulk_bp)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, port=5000)

