# 🧠 AI Digest

**AI Digest** is a FastAPI-based Gmail summarizer app.  
It connects to Gmail using Google OAuth2, fetches recent emails, and uses the OpenAI API to generate daily summaries.  
The app can even email you a daily digest automatically every morning.

---

## 🚀 Features
- Gmail OAuth2 authentication (read/send access)
- Fetches last 24 hours of emails
- Summarizes email content using OpenAI GPT models
- Sends summarized daily digest via Gmail
- Runs automatically every morning (scheduler)

---

## ⚙️ Tech Stack
- **Python 3.11+**
- **FastAPI**
- **Google API Client**
- **OpenAI API**
- **APScheduler**
- **dotenv**

---

## 🛠️ How to Run Locally
1. Clone the repository:
   ```bash
   git clone https://github.com/pradeepkorrapati45-wq/ai-digest.git
   cd ai-digest


2. Create a virtual environment and install dependencies:

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt


3. Add your environment variables in a .env file:

OPENAI_API_KEY=your_openai_key_here
GOOGLE_CLIENT_SECRET_FILE=client_secret.json
GOOGLE_TOKEN_FILE=token.json


4. Run the app:

uvicorn main:app --reload


Endpoints

/auth → Start Gmail authorization
/oauth2callback → Handles Gmail OAuth return
/test-digest → Fetches and summarizes last 24h emails
/send-digest → Emails summarized daily digest


Contact

Author: Bhanu Pradeep Korrapati
Email: pradeepkorrapati45@gmail.com