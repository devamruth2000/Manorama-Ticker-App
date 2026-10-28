# Live News Ticker Generation & Editorial Review Desk 📺

A full-stack, real-time editorial web application engineered to ingest raw news releases, synthesize punchy broadcast tickers under a strict 10-word ceiling, flag hallucination/drift against source facts, and export machine-readable transmission feeds for downstream broadcast automation.

---

## 🚀 Setup & Execution

### Prerequisites

- Python 3.10+
- Modern Web Browser (Chrome, Edge, Firefox, Safari)
- _(Optional)_ Google Gemini API Key

### 1. Installation

Clone the repository and set up a virtual environment:

```bash
git clone [https://github.com/devamruth2000/Editorial-Ai-Assistant.git](https://github.com/devamruth2000/Editorial-Ai-Assistant.git)
cd Editorial-Ai-Assistant

# Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install flask google-genai python-dotenv
```
