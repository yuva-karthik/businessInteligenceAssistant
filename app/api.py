from flask import Flask, jsonify, request

from app.database import load_csv
from app import analytics
from app.rules import answer_question


def create_app(test_config=None):
    app = Flask(__name__)

    if test_config:
        app.config.update(test_config)

    db_path = app.config.get("DB_PATH")
    csv_path = app.config.get("CSV_PATH")

    try:
        load_csv(
            csv_path=csv_path,
            db_path=db_path,
        )
        app.config["STARTUP_ERROR"] = None
    except Exception as exc:
        app.config["STARTUP_ERROR"] = str(exc)

    @app.get("/health")
    def health():
        if app.config.get("STARTUP_ERROR"):
            return jsonify({
                "status": "error",
                "detail": app.config["STARTUP_ERROR"],
            }), 500

        return jsonify({
            "status": "ok",
            "version": "v1-rule-based",
        })

    @app.get("/api/summary")
    def get_summary():
        if app.config.get("STARTUP_ERROR"):
            return jsonify({
                "error": app.config["STARTUP_ERROR"],
            }), 500

        return jsonify(analytics.summary(db_path))

    @app.post("/api/ask")
    def ask():
        if app.config.get("STARTUP_ERROR"):
            return jsonify({
                "error": app.config["STARTUP_ERROR"],
            }), 500

        body = request.get_json(silent=True)

        if not isinstance(body, dict):
            return jsonify({
                "error": "Send a JSON object containing 'question'.",
            }), 400

        question = body.get("question")

        if not isinstance(question, str) or not question.strip():
            return jsonify({
                "error": "'question' must be a non-empty string.",
            }), 400

        if len(question) > 500:
            return jsonify({
                "error": "Question must be 500 characters or fewer.",
            }), 400

        result = answer_question(question, db_path)

        return jsonify(result)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
    )