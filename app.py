import os
import re

import requests
from flask import Flask, jsonify, render_template, request

import db

app = Flask(__name__)

OLLAMA_URL = os.environ.get(
    "OLLAMA_URL", "http://127.0.0.1:11434"
)

OLLAMA_MODEL = os.environ.get(
    "OLLAMA_MODEL", "qwen2.5:0.5b"
)

SYSTEM_PROMPT = os.environ.get(
    "SYSTEM_PROMPT",
    "You are a helpful assistant. Respond briefly "
    "and in the same language as the user."
)

HISTORY_LIMIT = int(os.environ.get("HISTORY_LIMIT", "10"))
MAX_MESSAGE_LEN = 2000

SESSION_RE = re.compile(r"^[A-Za-z0-9-]{8,64}$")


@app.get("/")
def index():
    return render_template("index.html", model=OLLAMA_MODEL)


@app.get("/api/history/<session_id>")
def history(session_id):

    if not SESSION_RE.fullmatch(session_id):
        return jsonify(error="Invalid session ID"), 400

    try:
        return jsonify(db.get_history(session_id, limit=50))

    except db.DatabaseError:
        return jsonify(error="Database error"), 503


@app.post("/api/chat")
def chat():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(error="Invalid JSON request"), 400

    session_id = data.get("session_id", "")
    message = data.get("message", "")

    if not isinstance(session_id, str):
        return jsonify(error="Invalid session ID"), 400

    if not SESSION_RE.fullmatch(session_id):
        return jsonify(error="Invalid session ID"), 400

    if not isinstance(message, str) or not message.strip():
        return jsonify(error="Message is missing"), 400

    message = message.strip()

    if len(message) > MAX_MESSAGE_LEN:
        return jsonify(error="Message is too long"), 400

    # Retrieve history and save the new user message
    try:
        past = db.get_history(session_id, limit=HISTORY_LIMIT)
        db.save_message(session_id, "user", message)

    except db.DatabaseError:
        return jsonify(error="Database error"), 503

    # Build the conversation sent to Ollama
    messages = (
        [{"role": "system", "content": SYSTEM_PROMPT}]
        + past
        + [{"role": "user", "content": message}]
    )

    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False
    }

    # Generate the assistant response
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json=payload,
            timeout=120
        )

        response.raise_for_status()

        reply = response.json()["message"]["content"]

        if not isinstance(reply, str) or not reply.strip():
            raise ValueError("Invalid Ollama response")

    except (requests.RequestException, ValueError, KeyError, TypeError):
        return jsonify(error="Ollama request failed"), 502

    # Save the assistant response
    try:
        db.save_message(session_id, "assistant", reply)

    except db.DatabaseError:
        return jsonify(error="Failed to save response"), 503

    return jsonify(reply=reply)
