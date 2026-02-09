import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

HF_API_KEY = os.getenv("HF_API_KEY", "").strip()
HF_MODEL = os.getenv("HF_MODEL", "gpt-4o-mini")
ROUTER_URL = "https://router.huggingface.co/v1/chat/completions"

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

def generate_content(text, targets=None, n=3):
    if not text:
        return {"error": "Text required"}

    if not targets:
        targets = ["short_caption"]

    messages = build_prompt(text, targets, n)
    resp = call_hf(messages)

    if resp.get("error"):
        return fake_output(targets, n)

    try:
        content = resp["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception:
        return fake_output(targets, n)

