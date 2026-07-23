"""
Usage alerts for the Hethersett Grant Agent.

Sends a short email whenever the expensive research agent is used (a full or
targeted grant search). Configuration is read from environment variables; if
SMTP is not configured the sender quietly no-ops so it can never break a search.

Required env vars to enable alerts:
  SMTP_HOST       e.g. smtp.gmail.com
  SMTP_USER       the SMTP account username / from address
  SMTP_PASSWORD   the SMTP password (for Gmail, an App Password)

Optional:
  SMTP_PORT       default 587 (STARTTLS)
  ALERT_FROM      default falls back to SMTP_USER
  ALERT_TO        default jonf348@googlemail.com
"""

import os
import smtplib
import traceback
from datetime import datetime
from email.message import EmailMessage

DEFAULT_ALERT_TO = "jonf348@googlemail.com"


def _config() -> dict | None:
    host = os.getenv("SMTP_HOST")
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    if not (host and user and password):
        return None
    return {
        "host": host,
        "port": int(os.getenv("SMTP_PORT", "587")),
        "user": user,
        "password": password,
        "sender": os.getenv("ALERT_FROM") or user,
        "recipient": os.getenv("ALERT_TO") or DEFAULT_ALERT_TO,
    }


def send_agent_alert(search_type: str, job_id: int, question: str | None = None) -> None:
    """Email a notification that the agent has been used. Never raises."""
    cfg = _config()
    if cfg is None:
        print(f"[alert] SMTP not configured — skipping alert for {search_type} search job #{job_id}")
        return

    when = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    kind = "Targeted" if search_type == "targeted" else "Full"

    body_lines = [
        f"The Hethersett Grant Agent has been used.",
        "",
        f"Type:    {kind} grant search",
        f"Job:     #{job_id}",
        f"Started: {when}",
    ]
    if question:
        body_lines += ["", f"Question: {question}"]
    body_lines += [
        "",
        "This search calls the Anthropic API and typically costs a few pounds.",
    ]

    msg = EmailMessage()
    msg["Subject"] = f"Hethersett agent used — {kind.lower()} search (job #{job_id})"
    msg["From"] = cfg["sender"]
    msg["To"] = cfg["recipient"]
    msg.set_content("\n".join(body_lines))

    try:
        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=15) as server:
            server.starttls()
            server.login(cfg["user"], cfg["password"])
            server.send_message(msg)
        print(f"[alert] Sent usage alert for {search_type} search job #{job_id} to {cfg['recipient']}")
    except Exception as e:
        # Never let an alert failure affect the search itself.
        print(f"[alert] Failed to send usage alert for job #{job_id}: {e}")
        traceback.print_exc()
