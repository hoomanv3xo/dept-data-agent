from flask import Flask, jsonify, render_template, request

import agent

app = Flask(__name__)
MAX_QUESTION_CHARS = 500


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/ask")
def ask():
    question = (request.get_json(silent=True) or {}).get("question", "").strip()
    if not question:
        return jsonify(error="Type a question first."), 400
    if len(question) > MAX_QUESTION_CHARS:
        return jsonify(error=f"Keep questions under {MAX_QUESTION_CHARS} characters."), 400
    try:
        return jsonify(agent.ask(question))
    except Exception as e:  # network, key, or model errors
        app.logger.exception("agent failure")
        return jsonify(error="The assistant hit an error. Check the API key and try again."), 502


if __name__ == "__main__":
    app.run(debug=True)
