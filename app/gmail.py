import os
import base64
from fastapi.responses import RedirectResponse, JSONResponse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from dotenv import load_dotenv
from email.mime.text import MIMEText
from app.summarize import extract_plain_text

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send"
]

CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET_FILE", "client_secret.json")
TOKEN_FILE = os.getenv("GOOGLE_TOKEN_FILE", "token.json")

# ---------- FETCH FULL MESSAGES ----------
def get_full_messages_last_24h(service, limit=100):
    """Fetch full Gmail messages from the last 24h."""
    query = "newer_than:1d -category:social -category:promotions -in:chats"
    res = service.users().messages().list(userId="me", q=query, maxResults=limit).execute()
    ids = [m["id"] for m in res.get("messages", [])]
    full_msgs = []
    for mid in ids:
        full = service.users().messages().get(userId="me", id=mid, format="full").execute()
        full_msgs.append(full)
    return full_msgs



# ---------- AUTH FLOW ----------
def start_auth():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET,
        scopes=SCOPES,
        redirect_uri="http://localhost:8000/oauth2/callback"
    )
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )
    return RedirectResponse(auth_url)


def oauth_callback(code: str, state: str = ""):
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET,
        scopes=SCOPES,
        redirect_uri="http://localhost:8000/oauth2/callback"
    )
    flow.fetch_token(code=code)
    creds = flow.credentials
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())
    return JSONResponse({"ok": True, "message": "Gmail linked successfully! You can now call /test-digest."})


# ---------- GMAIL CLIENT ----------
def get_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


# ---------- FETCH EMAILS ----------
def fetch_last_24h(limit=100):
    service = get_service()
    full_msgs = get_full_messages_last_24h(service, limit=limit)
    out = []
    for full in full_msgs:
        headers = {h["name"]: h["value"] for h in full["payload"].get("headers", [])}
        subject = headers.get("Subject", "(No Subject)")
        sender  = headers.get("From", "")
        thread  = full.get("threadId", "")
        url     = f"https://mail.google.com/mail/u/0/#inbox/{thread}"
        body    = extract_plain_text(full)
        out.append({"subject": subject, "from": sender, "body": body, "url": url})
    return out


# ---------- SEND EMAIL ----------
def send_email(subject: str, html: str):
    service = get_service()
    profile = service.users().getProfile(userId="me").execute()
    to = profile["emailAddress"]

    message = MIMEText(html, "html")
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
