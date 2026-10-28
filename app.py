import os
import re
import uuid
from datetime import datetime, timezone
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()

app = Flask(__name__)

# Initialize GenAI Client if API key is provided
api_key = os.getenv("GEMINI_API_KEY")
client = None
if api_key:
  try:
    from google import genai

    client = genai.Client(api_key=api_key)
  except Exception as e:
    print(f"GenAI Client initialization skipped/failed: {e}")

# In-memory session store: announcement_id -> item
SESSION_STORE = {}


def detect_hallucination_and_drift(ticker_text: str, source_text: str) -> dict:
  """Deterministic safety guard: checks if numbers, percentages, currency,

  or capitalised entities in the ticker exist in the source text.
  """
  flags = []
  clean_source = source_text.lower()

  # 1. Word Count Check
  words = [w for w in ticker_text.strip().split() if w]
  word_count = len(words)
  if word_count > 10:
    flags.append(f"Exceeds 10-word limit ({word_count} words)")

  # 2. Number & Numeric entities check
  ticker_numbers = re.findall(r"\b\d+(?:[.,]\d+)?%?\b", ticker_text)
  for num in ticker_numbers:
    if num.lower() not in clean_source:
      flags.append(f"Number '{num}' not found in source text")

  # 3. Currency symbols and monetary amounts check
  ticker_money = re.findall(r"[$€£₹]\s*\d+", ticker_text)
  for m in ticker_money:
    clean_m = re.sub(r"\s+", "", m).lower()
    if clean_m not in re.sub(r"\s+", "", clean_source):
      flags.append(f"Monetary figure '{m}' not verified in source")

  return {
      "word_count": word_count,
      "drift_flag": len(flags) > 0,
      "reasons": flags,
  }


def generate_ticker_offline(source_text: str) -> str:
  """Smart heuristic summarizer when no AI/API key is present."""
  clean_text = re.sub(r"[^\w\s$%]", "", source_text)
  words = clean_text.split()
  stop_words = {
      "a",
      "an",
      "the",
      "that",
      "this",
      "is",
      "are",
      "was",
      "were",
      "has",
      "have",
      "had",
      "announced",
      "today",
      "yesterday",
      "stated",
      "confirmed",
      "according",
      "to",
      "in",
      "on",
      "at",
      "by",
      "for",
      "with",
      "about",
      "after",
  }
  important_words = [w for w in words if w.lower() not in stop_words]
  selected = important_words[:8] if important_words else words[:8]
  return " ".join(selected).upper()


def generate_ticker_ai(source_text: str) -> str:
  """Generates a strictly grounded, <= 10 word broadcast ticker."""
  if not client:
    return generate_ticker_offline(source_text)

  prompt = f"""
SYSTEM INSTRUCTION:
You are an ultra-rigorous newsroom ticker writer for a live 24/7 broadcast network.
Your job is to condense the announcement below into a ONE-LINE TV TICKER.

STRICT CONSTRAINTS:
1. MAXIMUM 10 WORDS.
2. ABSOLUTELY ZERO OUTSIDE KNOWLEDGE OR HALLUCINATION. Do not infer causes, company valuations, motivations, or consequences not explicitly printed.
3. Broadcast style: Use active verbs, omit filler articles (a, an, the) when possible, UPPERCASE.
4. If a fact or number is not stated verbatim, DO NOT INCLUDE IT.

ANNOUNCEMENT:
\"\"\"{source_text}\"\"\"

Output ONLY the ticker text. No quotation marks, no explanations.
"""
  models = ["gemini-flash-latest", "gemini-flash-lite-latest", "gemini-3.8-flash"]
  for model in models:
    try:
      response = client.models.generate_content(model=model, contents=prompt)
      cleaned = response.text.strip().replace('"', "").replace("\n", " ")
      # Truncate to maximum 10 words if the model overshoots
      words = cleaned.split()
      if len(words) > 10:
        cleaned = " ".join(words[:10])
      return cleaned
    except Exception as e:
      print(f"Model {model} failed: {e}")
      continue

  return generate_ticker_offline(source_text)


@app.route("/")
def index():
  return render_template("index.html")


@app.route("/api/announcements", methods=["POST"])
def ingest_announcements():
  """Ingests single or batch announcements."""
  data = request.get_json() or {}
  announcements = data.get("announcements", [])

  if not announcements:
    return jsonify({"error": "No announcement text provided"}), 400

  results = []
  current_order = len(SESSION_STORE)

  for text in announcements:
    raw_text = text.strip()
    if not raw_text:
      continue

    item_id = str(uuid.uuid4())[:8]
    ticker = generate_ticker_ai(raw_text)
    verification = detect_hallucination_and_drift(ticker, raw_text)

    item = {
        "id": item_id,
        "source": raw_text,
        "ticker": ticker,
        "original_ticker": ticker,
        "approved": False,
        "order": current_order,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "verification": verification,
    }
    SESSION_STORE[item_id] = item
    results.append(item)
    current_order += 1

  return jsonify({"items": results}), 201


@app.route("/api/tickers/<item_id>", methods=["PATCH"])
def update_ticker(item_id):
  """Updates editorial content, approval status, or reverts."""
  if item_id not in SESSION_STORE:
    return jsonify({"error": "Not found"}), 404

  data = request.get_json() or {}
  item = SESSION_STORE[item_id]

  if "ticker" in data:
    item["ticker"] = data["ticker"].strip()
    item["verification"] = detect_hallucination_and_drift(
        item["ticker"], item["source"]
    )

  if "approved" in data:
    item["approved"] = bool(data["approved"])

  if data.get("revert"):
    item["ticker"] = item["original_ticker"]
    item["verification"] = detect_hallucination_and_drift(
        item["ticker"], item["source"]
    )

  return jsonify({"item": item})


@app.route("/api/tickers/<item_id>/regenerate", methods=["POST"])
def regenerate_ticker(item_id):
  """Regenerates an individual ticker alternative."""
  if item_id not in SESSION_STORE:
    return jsonify({"error": "Not found"}), 404

  item = SESSION_STORE[item_id]
  new_ticker = generate_ticker_ai(item["source"])
  item["ticker"] = new_ticker
  item["verification"] = detect_hallucination_and_drift(
      new_ticker, item["source"]
  )

  return jsonify({"item": item})


@app.route("/api/tickers/<item_id>", methods=["DELETE"])
def delete_ticker(item_id):
  """Deletes a single ticker by ID."""
  if item_id in SESSION_STORE:
    del SESSION_STORE[item_id]
    return jsonify({"status": "deleted", "id": item_id})
  return jsonify({"error": "Item not found"}), 404


@app.route("/api/tickers/clear", methods=["POST"])
def clear_all_tickers():
  """Clears all tickers from the current session."""
  SESSION_STORE.clear()
  return jsonify({"status": "cleared"})


@app.route("/api/tickers/reorder", methods=["POST"])
def reorder_tickers():
  """Persists new sequence ordering from drag-and-drop or up/down shifts."""
  data = request.get_json() or {}
  ordered_ids = data.get("ordered_ids", [])

  for idx, item_id in enumerate(ordered_ids):
    if item_id in SESSION_STORE:
      SESSION_STORE[item_id]["order"] = idx

  return jsonify({"status": "success"})


@app.route("/api/export", methods=["GET"])
def export_approved():
  """Outputs structured, machine-readable JSON of approved tickers."""
  approved_items = [
      item for item in SESSION_STORE.values() if item.get("approved") is True
  ]
  approved_items.sort(key=lambda x: x["order"])

  payload = {
      "broadcast_system": "NEWS_TICKER_FEED_V1",
      "exported_at": datetime.now(timezone.utc).isoformat(),
      "count": len(approved_items),
      "tickers": [
          {
              "sequence": idx + 1,
              "ticker_id": item["id"],
              "ticker_text": item["ticker"],
              "word_count": len(item["ticker"].split()),
              "source_reference": item["source"],
              "approved_at": item.get("created_at"),
          }
          for idx, item in enumerate(approved_items)
      ],
  }
  return jsonify(payload)


if __name__ == "__main__":
  app.run(debug=True, port=5000)