from fastapi import FastAPI
from app.gmail import start_auth, oauth_callback, fetch_last_24h, send_email
from app.summarize import summarize_thread_items, compose_digest_html

app = FastAPI()

@app.get("/")
def home():
    return {"routes": ["/auth/google", "/test-digest", "/send-now"]}

@app.get("/auth/google")
def auth_google():
    return start_auth()

@app.get("/oauth2/callback")
def oauth2_callback(code: str, state: str = ""):
    return oauth_callback(code, state)

def build_digest_html(limit: int = 50) -> str:
    msgs = fetch_last_24h(limit=limit)
    items = summarize_thread_items(msgs)
    return compose_digest_html(items)

# returns JSON summaries count (debug)
@app.get("/test-digest")
def test_digest():
    msgs = fetch_last_24h(limit=50)
    items = summarize_thread_items(msgs)
    return {"ok": True, "summarized": len(items)}

# sends the actual email
@app.get("/send-now")
def send_now():
    html = build_digest_html(limit=50)
    send_email("Your Daily Email Digest (now)", html)
    return {"ok": True, "sent": True}


import os
from apscheduler.schedulers.background import BackgroundScheduler
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

# Default schedule: every day at 7:30 AM
DIGEST_HOUR = int(os.getenv("DIGEST_HOUR", "7"))
DIGEST_MINUTE = int(os.getenv("DIGEST_MINUTE", "30"))
TIMEZONE = os.getenv("TIMEZONE", "America/Chicago")

sched: BackgroundScheduler | None = None

def send_daily_job():
    from app.gmail import send_email, fetch_last_24h
    from app.summarize import summarize_thread_items, compose_digest_html

    try:
        msgs = fetch_last_24h(limit=50)
        items = summarize_thread_items(msgs)
        html = compose_digest_html(items)
        send_email("Your Daily AI Digest ☀️", html)
        print("✅ Daily digest sent successfully.")
    except Exception as e:
        print("❌ Error sending daily digest:", e)

@app.on_event("startup")
def start_scheduler():
    global sched
    sched = BackgroundScheduler(timezone=ZoneInfo(TIMEZONE))
    sched.add_job(send_daily_job, "cron", hour=DIGEST_HOUR, minute=DIGEST_MINUTE)
    sched.start()
    print(f"🕒 Scheduler started: {TIMEZONE} at {DIGEST_HOUR:02d}:{DIGEST_MINUTE:02d}")

@app.on_event("shutdown")
def stop_scheduler():
    if sched:
        sched.shutdown()
