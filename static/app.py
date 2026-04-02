from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
import anthropic, json, os, hashlib
from datetime import datetime
from pathlib import Path

app = Flask(__name__, static_folder="static")
app.secret_key = os.urandom(32)
CORS(app, supports_credentials=True)

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

USERS = {
    "jacobmillen": hashlib.sha256("moonlanding101".encode()).hexdigest()
}

def get_client():
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None
    return anthropic.Anthropic(api_key=key)

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def memory_path(username):
    return DATA_DIR / (username + "_memory.json")

def load_memory(username):
    p = memory_path(username)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except:
            pass
    return {
        "user_name": username,
        "facts": [],
        "preferences": {},
        "notes": [],
        "conversation_summaries": [],
        "custom_shortcuts": {},
        "research_topics": [],
        "chat_history": []
    }

def save_memory(username, mem):
    mem["last_seen"] = datetime.now().isoformat()
    memory_path(username).write_text(json.dumps(mem, indent=2))

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username", "").strip().lower()
    password = data.get("password", "")
    if USERS.get(username) == hash_pw(password):
        session["user"] = username
        mem = load_memory(username)
        save_memory(username, mem)
        return jsonify({"success": True, "message": "Welcome back, FRIDAY is online."})
    return jsonify({"success": False, "message": "Invalid login"}), 401

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})

@app.route("/api/me", methods=["GET"])
def me():
    return jsonify({"logged_in": "user" in session, "username": session.get("user")})

@app.route("/api/chat", methods=["POST"])
def chat():
    if "user" not in session:
        return jsonify({"error": "Not logged in"}), 401
    username = session["user"]
    data = request.json
    message = data.get("message", "").strip()

    client = get_client()
    if not client:
        return jsonify({"reply": "API key not set. Contact admin."})

    mem = load_memory(username)
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=700,
        system="You are FRIDAY, a helpful and witty AI assistant.",
        messages=[{"role": "user", "content": message}]
    )
    reply = response.content[0].text
    return jsonify({"reply": reply, "agent_commands": []})

@app.route("/api/memory", methods=["GET"])
def get_memory():
    if "user" not in session:
        return jsonify({"error": "Not logged in"}), 401
    return jsonify({"facts": [], "notes": [], "preferences": {}, "research_topics": []})

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
