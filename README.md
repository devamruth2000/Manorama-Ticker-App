# Live News Ticker Generation & Editorial Review Desk 📺

A full-stack editorial workbench engineered to condense raw news releases into punchy broadcast tickers under a strict 10-word constraint, flag numeric and entity hallucinations in real time, enable live editorial review/reordering, and export machine-readable transmission feeds for broadcast automation.

---

## 🚀 Setup & Execution

### Prerequisites

- Python 3.10+
- Modern Web Browser (Chrome, Edge, Firefox, Safari)
- _(Optional)_ Google Gemini API Key

### 1. Installation & Environment Setup

Clone the repository and set up a virtual environment:

```bash
git clone [https://github.com/devamruth2000/Manorama-Ticker-App.git](https://github.com/devamruth2000/Manorama-Ticker-App.git)
cd Manorama-Ticker-App

# Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install flask google-genai python-dotenv
2. Environment Configuration (Optional)
Create a .env file in the project root:

Code snippet
GEMINI_API_KEY=your_gemini_api_key_here
Offline Evaluation Guarantee: If no API key is supplied, the application automatically runs using an internal deterministic heuristic engine. The server boots, generates tickers, supports multi-cycle regeneration, and exports valid JSON without internet or API dependencies.

3. Run the Application
Bash
python app.py
Open your browser and navigate to:

Plaintext
[http://127.0.0.1:5000](http://127.0.0.1:5000)


```

Project Summary: Live News Ticker DeskProject Objective: A full-stack, broadcast-style web desk engineered to ingest raw news announcements, condense them into strict $\le 10$-word tickers, flag hallucinations/drift, enable live editorial review/reordering, and export machine-readable transmission feeds
.Tech Stack:
Backend: Python (Flask) with REST endpoints (/api/announcements, /api/tickers/<id>, /api/export).
Frontend: Vanilla HTML5, CSS3, and JavaScript featuring a dual-intake interface, draggable/shiftable cards, and a live broadcast marquee scroller.
AI & Fallback: Google Gemini API (google-genai SDK) for generative distillation, paired with a deterministic pure-Python heuristic engine for zero-dependency offline operation.
Core Mechanisms:
Fidelity & Zero-Hallucination: Grounded negative prompt directives coupled with an algorithmic server-side regex validator that checks numbers, percentages, and currencies against the source text to trigger ⚠️ Drift Detected alerts.
Length Enforcement: Generative hard boundary combined with real-time client-side word-count metering ($\le 10$ words).
Editorial Controls: Source-text visibility, in-place editing, sequential reordering, multi-variation regeneration (⚡ Regen), undo/revert (↺ Undo), card deletion (✕), and list wiping (🗑️ Clear All).
Broadcast JSON Export: Formatted endpoint (GET /api/export) delivering sequence-indexed approved tickers with metadata for downstream newsroom character generators.
Deployment Repository: Active, clean, and documented at [https://github.com/devamruth2000/Manorama-Ticker-App](https://github.com/devamruth2000/Manorama-Ticker-App).
