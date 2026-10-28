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
