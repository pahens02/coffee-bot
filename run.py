from flask import Flask, request, jsonify
from app.routes import routes

app = Flask(__name__)

# Register blueprints or routes
app.register_blueprint(routes)


@app.route("/")
def index():
    return "Slack Bot is running!", 200


if __name__ == "__main__":
    app.run(debug=True)
