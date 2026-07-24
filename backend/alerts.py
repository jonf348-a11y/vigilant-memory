"""
Usage alerts for the Hethersett Grant Agent.

Sends a short email whenever the expensive research agent is used (a full or
targeted grant search). Delivery is via the Resend HTTPS API rather than SMTP,
because Railway's Hobby plan blocks outbound SMTP ports. Configuration is read
from environment variables; if RESEND_API_KEY is not set the sender quietly
no-ops so it can never break a search.

Required env var to enable alerts:
  RESEND_API_KEY   your Resend API key (starts with "re_")

Optional:
  ALERT_FROM       sender address. Default "onboarding@resend.dev", which is
                   Resend's shared sender that works with no domain setup.
  ALERT_TO         recipient. Default jonf348@googlemail.com. On Resend's free
                   tier without a verified domain this must be the address you
                   signed up to Resend with.
"""

import json
import os
import traceback
import urllib.error
import urllib.request
from datetime import datetime

DEFAULT_ALERT_TO = "jonf348@googlemail.com"
DEFAULT_ALERT_FROM = "Hethersett Agent <onboarding@resend.dev>"
RESEND_ENDPOINT = "https://api.resend.com/emails"


def _config() -> dict | None:
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        return None
    return {
        "api_key": api_key,
        "sender": os.getenv("ALERT_FROM") or DEFAULT_ALERT_FROM,
        "recipient": os.getenv("ALERT_TO") or DEFAULT_ALERT_TO,
    }


def send_agent_alert(search_type: str, job_id: int, question: str | None = None) -> None:
    """Email a notification that the agent has been used. Never raises."""
    cfg = _config()
    if cfg is None:
        print(f"[alert] RESEND_API_KEY not set — skipping alert for {search_type} search job #{job_id}")
        return

    when = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    kind = "Targeted" if search_type == "targeted" else "Full"

    body_lines = [
        "The Hethersett Grant Agent has been used.",
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

    payload = json.dumps({
        "from": cfg["sender"],
        "to": [cfg["recipient"]],
        "subject": f"Hethersett agent used — {kind.lower()} search (job #{job_id})",
        "text": "\n".join(body_lines),
    }).encode("utf-8")

    req = urllib.request.Request(
        RESEND_ENDPOINT,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {cfg['api_key']}",
            "Content-Type": "application/json",
            # Resend sits behind Cloudflare, which 403s the default urllib
            # User-Agent (Cloudflare error 1010). A named UA passes.
            "User-Agent": "hethersett-grant-agent/1.0",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
        print(f"[alert] Sent usage alert for {search_type} search job #{job_id} to {cfg['recipient']}")
    except urllib.error.HTTPError as e:
        # Resend returns a JSON error body — surface it to help diagnose config issues.
        detail = e.read().decode("utf-8", "replace")
        print(f"[alert] Resend rejected alert for job #{job_id} (HTTP {e.code}): {detail}")
    except Exception as e:
        # Never let an alert failure affect the search itself.
        print(f"[alert] Failed to send usage alert for job #{job_id}: {e}")
        traceback.print_exc()
