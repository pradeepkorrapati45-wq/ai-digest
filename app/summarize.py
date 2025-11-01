import os, json, re, html, base64
from typing import List, Dict, Optional
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY not found. Please set it in your .env file.")


client = OpenAI(api_key=api_key)

# --------- Helpers: clean email bodies ---------
def _decode_part(part):
    data = part.get("body", {}).get("data")
    if not data:
        return ""
    try:
        return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")
    except Exception:
        return ""

def extract_plain_text(message: Dict) -> str:
    """Return best-effort plain text from a Gmail message resource."""
    payload = message.get("payload", {})
    mime_type = payload.get("mimeType", "")

    # simple text/plain
    if mime_type == "text/plain":
        return _strip_noise(_decode_part(payload))

    # multipart: look for text/plain first, then text/html
    if "parts" in payload:
        text = ""
        html_text = ""
        for p in payload["parts"]:
            mt = p.get("mimeType", "")
            if mt == "text/plain" and not text:
                text = _decode_part(p)
            elif mt == "text/html" and not html_text:
                html_text = _decode_part(p)
        if text:
            return _strip_noise(text)
        if html_text:
            return _strip_noise(_html_to_text(html_text))

    # fallback to snippet
    return _strip_noise(message.get("snippet", ""))

def _html_to_text(s: str) -> str:
    # tiny HTML->text (no extra deps)
    s = re.sub(r"(?is)<(script|style).*?>.*?</\1>", "", s)
    s = re.sub(r"(?is)<br\s*/?>", "\n", s)
    s = re.sub(r"(?is)</p>", "\n\n", s)
    s = re.sub(r"(?is)<.*?>", "", s)
    return html.unescape(s)

def _strip_noise(s: str, limit: int = 4000) -> str:
    # trim quoted replies / signatures (naive), collapse whitespace, cap length
    for marker in ["-----Original Message-----", "On ", "wrote:", "From:"]:
        i = s.find(marker)
        if i > 200:  # keep short intros
            s = s[:i]
            break
    s = re.sub(r"\s+\n", "\n", s)
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()[:limit]

# --------- OpenAI prompts ---------
_SUM_SYS = "You produce concise, executive email digests. Respond with VALID JSON only."
_SUM_USER = """Summarize this email as JSON with keys:
{{
  "title": "≤80 chars subject-style",
  "why_it_matters": "1–2 short sentences",
  "action": "clear next step or ''",
  "owner": "me|them|''",
  "due_date": "YYYY-MM-DD or ''"
}}
Subject: {subject}
From: {sender}
Body:
{body}
Only return JSON, nothing else.
"""

def _parse_json(s: str) -> Optional[dict]:
    try:
        return json.loads(s)
    except Exception:
        m = re.search(r"\{.*\}$", s.strip(), re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
        return None

# --------- Public API ---------
def summarize_thread_items(items: List[Dict]) -> List[Dict]:
    """items: list of dicts with subject, from, body, url. Returns ranked summaries."""
    out = []
    for m in items[:30]:  # cap for cost
        prompt = _SUM_USER.format(
            subject=m.get("subject",""),
            sender=m.get("from",""),
            body=(m.get("body","") or "")[:1200]
        )
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"system","content":_SUM_SYS},
                      {"role":"user","content":prompt}],
            temperature=0.2
        )
        js = _parse_json(r.choices[0].message.content) or {
            "title": m.get("subject","(no subject)"),
            "why_it_matters": "",
            "action": "", "owner": "", "due_date": ""
        }

        # cheap importance score (hybrid later)
        body = (m.get("body") or "").lower()
        score = 0
        if "?" in body or "please" in body: score += 1
        if any(w in body for w in ["today","tomorrow","deadline","invoice","approve","schedule"]): score += 1
        if "<" not in m.get("from",""): score += 1  # crude non-list bonus

        out.append({**js, "url": m.get("url",""), "score": score})

    out.sort(key=lambda x: x["score"], reverse=True)
    return out

def compose_digest_html(items: List[Dict]) -> str:
    top = items[:5]
    rest = items[5:15]
    def li(e):
        act = f"<div><i>Action:</i> {e['action']}</div>" if e.get("action") else ""
        return f'<li><a href="{e.get("url","#")}" target="_blank"><b>{e["title"]}</b></a><div>{e["why_it_matters"]}</div>{act}</li>'
    return f"""
    <html><body style="font-family:Arial,Helvetica,sans-serif;line-height:1.45">
      <h2>Top 5 — Must Know</h2>
      <ol>{''.join(li(e) for e in top)}</ol>
      <h3>Other Highlights</h3>
      <ul>{''.join(li(e) for e in rest)}</ul>
      <hr/><small>AI Digest · generated locally</small>
    </body></html>
    """
