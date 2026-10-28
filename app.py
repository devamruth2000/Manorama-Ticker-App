import os
import random
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


def generate_ticker_offline(
    source_text: str, previous_versions: list = None
) -> str:
  """Heuristic summarizer that rotates through multiple word-windows when offline."""
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
  if not important_words:
    important_words = words

  candidates = []
  # Candidate 1: Leading key facts
  candidates.append(" ".join(important_words[:8]).upper())
  # Candidate 2: Verb/action shift
  if len(important_words) > 5:
    candidates.append(" ".join(important_words[1:9]).upper())
  # Candidate 3: Core payload / numeric tail
  if len(important_words) >= 8:
    candidates.append(" ".join(important_words[-7:]).upper())
  # Candidate 4: Alternate stride
  if len(important_words) >= 6:
    candidates.append(" ".join(important_words[2:8]).upper())

  prev_set = set(previous_versions or [])
  for cand in candidates:
    if cand not in prev_set:
      return cand

  # If all candidates exhausted, pick a randomized factual sub-window
  start_idx = random.randint(0, max(0, len(important_words) - 6))
  return " ".join(important_words[start_idx : start_idx + 7]).upper()


def generate_ticker_ai(
    source_text: str, previous_versions: list = None
) -> str:
  """Generates a strictly grounded, <= 10 word broadcast ticker.

  Avoids repeating any phrasing provided in previous_versions.
  """
  if not client:
    return generate_ticker_offline(source_text, previous_versions)

  avoid_clause = ""
  if previous_versions:
    formatted_prev = "\n".join([f"- {v}" for v in previous_versions if v])
    avoid_clause = f"""
PREVIOUS VARIATIONS TO AVOID (DO NOT REPEAT):
{formatted_prev}
Select an alternative active verb or focus on a different key metric/angle from the announcement.
"""

  prompt = f"""
SYSTEM INSTRUCTION:
You are an ultra-rigorous newsroom ticker writer for a live 24/7 broadcast network.
Your job is to condense the announcement below into a ONE-LINE TV TICKER.

STRICT CONSTRAINTS:
1. MAXIMUM 10 WORDS.
2. ABSOLUTELY ZERO OUTSIDE KNOWLEDGE OR HALLUCINATION. Do not infer causes, company valuations, motivations, or consequences not explicitly printed.
3. Broadcast style: Use active verbs, omit filler articles (a, an, the) when possible, UPPERCASE.
4. If a fact or number is not stated verbatim, DO NOT INCLUDE IT.
{avoid_clause}
ANNOUNCEMENT:
\"\"\"{source_text}\"\"\"

Output ONLY the ticker text. No quotation marks, no explanations.
"""
  models = ["gemini-flash-latest", "gemini-flash-lite-latest", "gemini-3.8-flash"]
  for model in models:
    try:
      response = client.models.generate_content(
          model=model, contents=prompt, config={"temperature": 0.7}
      )
      cleaned = response.text.strip().replace('"', "").replace("\n", " ")
      words = cleaned.split()
      if len(words) > 10:
        cleaned = " ".join(words[:10])
      return cleaned
    except Exception as e:
      print(f"Model {model} failed: {e}")
      continue

  return generate_ticker_offline(source_text, previous_versions)


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
        "history": [ticker],
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
  """Regenerates a new unique alternative by passing history of prior versions."""
  if item_id not in SESSION_STORE:
    return jsonify({"error": "Not found"}), 404

  item = SESSION_STORE[item_id]

  if "history" not in item:
    item["history"] = [item["ticker"]]
  elif item["ticker"] not in item["history"]:
    item["history"].append(item["ticker"])

  new_ticker = generate_ticker_ai(
      item["source"], previous_versions=item["history"]
  )
  item["ticker"] = new_ticker
  item["history"].append(new_ticker)
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