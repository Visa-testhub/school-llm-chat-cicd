import os

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

OLLAMA_URL = os.environ.get(
    "OLLAMA_URL", "http://127.0.0.1:11434"
)

OLLAMA_MODEL = os.environ.get(
    "OLLAMA_MODEL", "qwen2.5:0.5b"
)


@app.get("/")
def index():
    return "LLM Chat - Backend is running!"


@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()

    if not message:
        return jsonify(error="Message is missing"), 400

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {
                "role": "user",
                "content": message
            }
        ],
        "stream": False
    }

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json=payload,
            timeout=120
        )
        response.raise_for_status()

        reply = response.json()["message"]["content"]

        return jsonify(reply=reply)

    except requests.RequestException:
        return jsonify(error="Ollama request failed"), 502
