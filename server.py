# server.py — AI Repurpose App Backend (FINAL FIXED VERSION)

import os
import sys
import time
import json
import random
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

# ================= ENV =================
load_dotenv()

HF_API_KEY = os.getenv("HF_API_KEY", "").strip()
HF_MODEL = os.getenv("HF_MODEL", "gpt-4o-mini")
ROUTER_URL = "https://router.huggingface.co/v1/chat/completions"

# ================= PATH FIX (FOR EXE) =================
if hasattr(sys, "_MEIPASS"):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# ================= APP =================
app = Flask(
    __name__,
    static_folder=FRONTEND_DIR,
    static_url_path=""
)
CORS(app)

# ================= DEBUG =================
print("BASE_DIR:", BASE_DIR)
print("FRONTEND_DIR:", FRONTEND_DIR)
if os.path.exists(FRONTEND_DIR):
    print("FRONTEND FILES:", os.listdir(FRONTEND_DIR))
else:
    print("FRONTEND DIR NOT FOUND")

# ================= FRONTEND ROUTES =================
@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory(FRONTEND_DIR, path)

# ================= AI CONFIG =================
AVAILABLE_TARGETS = [
   "short_caption",
    "title",
    "tl_dr",
    "hashtags",
    "tweet_thread",
    "instagram_carousel_captions",
    "reel_script_30s",
    "linkedin_post",
    "youtube_description",
    "email_subjects_preview",
    "blog_intro",
    "faq_questions",
    "product_bullets",
    "meta_description",
    "ad_headline",
    "quote_graphic",
    "image_alt_text"
]

def system_prompt():
    return (
        "You are an expert content repurposer. "
        "Return ONLY valid JSON. "
        "Each target must contain an ARRAY of variations."
    )

def build_prompt(text, targets, n):
    return [
        {"role": "system", "content": system_prompt()},
        {"role": "user", "content": f"""
Input content:
'''{text}'''

Targets: {', '.join(targets)}
Variations per target: {n}

Return ONLY valid JSON.
"""}
    ]

def call_hf(messages):
    if not HF_API_KEY:
        return {"error": "HF_API_KEY missing"}

    payload = {
        "model": HF_MODEL,
        "messages": messages,
        "max_tokens": 700,
        "temperature": 0.7
    }

    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        r = requests.post(ROUTER_URL, headers=headers, json=payload, timeout=30)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def fake_output(targets, n):
    out = {}
    for t in targets:
        out[t] = [f"{t} variation {i+1}" for i in range(n)]
    return out

# ================= API =================
@app.route("/repurpose", methods=["POST"])
def repurpose():
    data = request.get_json(force=True, silent=True) or {}
    text = data.get("text", "").strip()
    targets = data.get("targets", ["short_caption"])
    n = int(data.get("n_variations", 3))

    if not text:
        return jsonify({"ok": False, "error": "Text required"}), 400

    messages = build_prompt(text, targets, n)
    resp = call_hf(messages)

    if resp.get("error"):
        return jsonify({
            "ok": True,
            "results": fake_output(targets, n),
            "debug": resp
        })

    try:
        content = resp["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        return jsonify({"ok": True, "results": parsed})
    except Exception:
        return jsonify({
            "ok": True,
            "results": fake_output(targets, n),
            "debug": "json_parse_error"
        })

# ================= HEALTH =================
@app.route("/health")
def health():
    return jsonify({"status": "ok", "time": int(time.time())})

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

