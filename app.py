#!/usr/bin/env python3
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

# Optional: SocketIO for real-time updates (degrades gracefully if not used on some hosts)
from flask_socketio import SocketIO, emit

load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure SocketIO (threading is fine for demo)
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Load Baseline data (sample subset) ---
DATA_DIR = Path(__file__).parent / "data"
BASELINE_JSON = DATA_DIR / "baseline_features.json"

if BASELINE_JSON.exists():
    with open(BASELINE_JSON, "r", encoding="utf-8") as f:
        BASELINE = json.load(f)
else:
    BASELINE = {"features": []}

def check_features(tech_stack: List[str]) -> Dict[str, Any]:
    """
    Given a list of feature keys, return baseline compatibility and notes.
    """
    results = []
    features = {f["id"]: f for f in BASELINE.get("features", [])}
    for key in tech_stack:
        f = features.get(key)
        if f:
            results.append(f)
    return {"count": len(results), "results": results}

def ai_suggest(project_type: str, language: str, use_case: str) -> Dict[str, Any]:
    """
    Very lightweight on-server suggestion engine; uses OpenAI if key provided.
    """
    suggestion_blocks = []
    # 1) Local heuristics (fast + deterministic)
    heuristics = {
        "web app": ["pwa", "fetch-api", "web-components"],
        "extension": ["web-extensions", "manifest-v3", "storage-api"],
        "docs tool": ["mdn-compat-data", "clipboard-api", "modules"],
        "analytics": ["performance-api", "long-tasks", "resource-timing"],
        "ai demo": ["webgpu", "offscreen-canvas", "sharedarraybuffer"]
    }
    stack = heuristics.get(project_type.lower().strip(), ["modules", "fetch-api"])

    base_plan = [
        f"Initialize a {language} {project_type} with Flask backend + HTML/JS frontend.",
        "Wire a /api/baseline-check endpoint using local Baseline JSON.",
        "Expose a dashboard to visualize 'safe-to-use' features and caveats.",
        "Ship a CLI seed: `flask --app app.py run` for quickstart.",
        "Add GitHub Actions for lint/tests (future).",
    ]

    suggestion_blocks.append({"title": "Starter Plan", "items": base_plan})
    suggestion_blocks.append({"title": "Recommended Web Features", "items": stack})

    # 2) Optional: augment via OpenAI if key exists
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if openai_key:
        try:
            # Using OpenAI Chat Completions style prompt (no external calls if offline)
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            prompt = (
                "You are an expert hackathon mentor. In 6 bullet points, propose a tight, "
                f"high-impact plan for a '{project_type}' using '{language}' to showcase Baseline web features "
                f"for the use case: '{use_case}'. Keep it practical and specific."
            )
            resp = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[{"role":"system","content":"Be concise and practical."},
                          {"role":"user","content":prompt}],
                max_tokens=300,
                temperature=0.3
            )
            text = resp.choices[0].message.content
            # Naive split
            bullets = [line.strip("-• ").strip() for line in text.split("\n") if line.strip()][:8]
            if bullets:
                suggestion_blocks.append({"title": "AI Mentor Plan", "items": bullets})
        except Exception as e:
            suggestion_blocks.append({"title":"AI Mentor Plan (skipped)", "items":[f"AI call failed or not configured: {e}"]})

    return {"project_type": project_type, "language": language, "use_case": use_case, "suggestions": suggestion_blocks}

@app.route("/")
def index():
    return render_template("dashboard.html", now=datetime.utcnow())

@app.route("/api/suggest", methods=["POST"])
def api_suggest():
    data = request.get_json(force=True)
    project_type = data.get("project_type", "web app")
    language = data.get("language", "Python")
    use_case = data.get("use_case", "demo")
    payload = ai_suggest(project_type, language, use_case)
    # Emit a live update for connected dashboards
    socketio.emit("suggestion_event", payload, broadcast=True)
    return jsonify(payload)

@app.route("/api/baseline-check", methods=["POST"])
def api_baseline_check():
    data = request.get_json(force=True)
    features = data.get("features", [])
    result = check_features(features)
    socketio.emit("baseline_event", result, broadcast=True)
    return jsonify(result)

@app.route("/health")
def health():
    return jsonify({"ok": True, "time": datetime.utcnow().isoformat()})

# Static helper (optional)
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

if __name__ == "__main__":
    # Use socketio.run so websockets work locally
    socketio.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "5050")), debug=True)
