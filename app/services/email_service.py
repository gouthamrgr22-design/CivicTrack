"""CivicTrack V3 Resend email delivery using Python's standard library."""

import json
import os
import re
import urllib.error
import urllib.request

from email.utils import parseaddr
from html import escape
from pathlib import Path
from urllib.parse import quote, urlsplit

RESEND_API_URL = "https://api.resend.com/emails"


def load_environment():
    project_root = Path(__file__).resolve().parents[2]
    environment_file = project_root / ".env"
    if not environment_file.is_file():
        return

    for raw_line in environment_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if not key.isidentifier():
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        os.environ.setdefault(key, value)


def get_email_config():
    load_environment()
    required = ("RESEND_API_KEY", "RESEND_FROM", "CIVICTRACK_BASE_URL")
    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        raise RuntimeError(
            "Resend email service is not configured. Missing: " + ", ".join(missing)
        )

    api_key = os.environ["RESEND_API_KEY"].strip()
    sender = os.environ["RESEND_FROM"].strip()
    sender_email = parseaddr(sender)[1]
    if not api_key.startswith("re_") or "\r" in api_key or "\n" in api_key:
        raise RuntimeError("RESEND_API_KEY is invalid.")
    if not sender_email or "@" not in sender_email or "\r" in sender or "\n" in sender:
        raise RuntimeError("RESEND_FROM must be a valid email sender address.")

    base_url = os.environ["CIVICTRACK_BASE_URL"].rstrip("/")
    parsed = urlsplit(base_url)
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.netloc
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
    ):
        raise RuntimeError("CIVICTRACK_BASE_URL must be a valid HTTP or HTTPS origin.")
    if parsed.hostname not in ("localhost", "127.0.0.1", "::1") and parsed.scheme != "https":
        raise RuntimeError("Public CivicTrack deployments must use HTTPS.")

    return {"api_key": api_key, "sender": sender, "base_url": base_url}


def send_email(recipient, subject, text_body, html_body=None, idempotency_key=None):
    config = get_email_config()
    if (
        not isinstance(recipient, str)
        or not recipient.strip()
        or "@" not in recipient
        or "\r" in recipient
        or "\n" in recipient
    ):
        raise ValueError("Invalid recipient email address.")
    if not isinstance(subject, str) or not subject.strip() or "\r" in subject or "\n" in subject:
        raise ValueError("Invalid email subject.")
    if not isinstance(text_body, str):
        raise ValueError("Email body must be text.")
    if html_body is not None and not isinstance(html_body, str):
        raise ValueError("HTML email body must be text.")

    payload = {
        "from": config["sender"],
        "to": [recipient.strip()],
        "subject": subject,
        "text": text_body,
    }
    if html_body is not None:
        payload["html"] = html_body

    headers = {
        "Authorization": "Bearer " + config["api_key"],
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if isinstance(idempotency_key, str) and re.fullmatch(r"[A-Za-z0-9_./:-]{1,256}", idempotency_key):
        headers["Idempotency-Key"] = idempotency_key

    request = urllib.request.Request(
        RESEND_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.loads(response.read(65536).decode("utf-8"))
            if response.status not in (200, 201) or not isinstance(result, dict) or not result.get("id"):
                raise RuntimeError("Resend returned an incomplete email response.")
    except urllib.error.HTTPError as error:
        raise RuntimeError(
            "Resend rejected the email request. Check your API key, sender domain, and account status."
        ) from error
    except (OSError, urllib.error.URLError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("Resend email delivery could not be reached.") from error
    return result["id"]


def send_verification_email(recipient, full_name, token):
    if not isinstance(token, str) or not token:
        raise ValueError("Invalid verification token.")
    if not isinstance(full_name, str):
        full_name = "CivicTrack member"

    config = get_email_config()
    verification_url = (
        config["base_url"]
        + "/templates/verify_email.html#token="
        + quote(token, safe="")
    )
    safe_name = escape(full_name)
    safe_url = escape(verification_url, quote=True)

    subject = "Verify your CivicTrack email address"
    text_body = f"""Hello {full_name},

Welcome to CivicTrack!

Please open this link to verify your email address:

{verification_url}

This link expires in 30 minutes and can only be used once.

If you did not create this account, you can ignore this email.

CivicTrack Team
"""
    html_body = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Verify CivicTrack email</title></head>
<body style="margin:0;padding:35px 15px;background:#080f1d;color:#eaf2ff;font-family:Arial,sans-serif;">
<div style="max-width:520px;margin:auto;padding:35px;background:#111d30;border:1px solid #263750;border-radius:16px;">
<h1 style="color:#60a5fa;">CivicTrack</h1><h2>Welcome, {safe_name}!</h2>
<p style="color:#b7c6da;line-height:1.8;">Verify your email address to finish setting up your CivicTrack account.</p>
<a href="{safe_url}" style="display:inline-block;margin:20px 0;padding:14px 24px;border-radius:8px;background:#2563eb;color:white;text-decoration:none;font-weight:bold;">Verify Email Address</a>
<p style="color:#9aacbf;font-size:12px;">This link expires in 30 minutes and can only be used once.</p>
<p style="color:#9aacbf;font-size:12px;">If you did not create this account, ignore this message.</p>
<hr style="border:1px solid #263750;"><p style="color:#71849e;font-size:11px;">CivicTrack · Building better communities together.</p>
</div></body></html>"""

    return send_email(
        recipient,
        subject,
        text_body,
        html_body,
        idempotency_key="civictrack-email-verification/" + token,
    )
