
"""
CivicTrack V3 — Email Delivery Service

Provider-independent SMTP integration.

Supports:
- Email verification
- Complaint notifications (future integration)
- Secure SMTP connections
- Environment-based configuration

Never stores or exposes email provider credentials.
"""

import os
import smtplib
import ssl

from email.message import EmailMessage
from email.utils import formataddr
from html import escape
from pathlib import Path
from urllib.parse import quote, urlsplit


# =====================================================
# ENVIRONMENT CONFIGURATION
# =====================================================

def load_environment():

    project_root = Path(__file__).resolve().parents[2]
    environment_file = project_root / ".env"

    if not environment_file.is_file():
        return

    for line in environment_file.read_text(
        encoding="utf-8"
    ).splitlines():

        line = line.strip()

        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[7:].strip()

        if "=" not in line:
            continue

        key, value = line.split("=", 1)

        key = key.strip()
        value = value.strip()

        if not key.isidentifier():
            continue

        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in ("'", '"')
        ):
            value = value[1:-1]

        os.environ.setdefault(key, value)


def get_email_config():

    load_environment()

    required = (
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USERNAME",
        "SMTP_PASSWORD",
        "SMTP_FROM",
        "CIVICTRACK_BASE_URL",
    )

    missing = [
        name
        for name in required
        if not os.environ.get(name)
    ]

    if missing:

        raise RuntimeError(
            "Email service is not configured. "
            "Missing: " + ", ".join(missing)
        )

    try:

        port = int(os.environ["SMTP_PORT"])

    except ValueError as error:

        raise RuntimeError(
            "SMTP_PORT must be a valid port number."
        ) from error

    if not 1 <= port <= 65535:
        raise RuntimeError("Invalid SMTP port.")

    base_url = os.environ["CIVICTRACK_BASE_URL"].rstrip("/")

    parsed_url = urlsplit(base_url)

    if (
        parsed_url.scheme not in ("http", "https")
        or not parsed_url.netloc
        or parsed_url.query
        or parsed_url.fragment
    ):
        raise RuntimeError(
            "CIVICTRACK_BASE_URL must be a valid HTTP or HTTPS origin."
        )

    local_hosts = ("localhost", "127.0.0.1", "::1")

    if (
        parsed_url.hostname not in local_hosts
        and parsed_url.scheme != "https"
    ):
        raise RuntimeError(
            "Public CivicTrack deployments must use HTTPS."
        )

    config = {

        "host": os.environ["SMTP_HOST"],
        "port": port,
        "username": os.environ["SMTP_USERNAME"],
        "password": os.environ["SMTP_PASSWORD"],
        "sender": os.environ["SMTP_FROM"],
        "sender_name": os.environ.get(
            "SMTP_FROM_NAME",
            "CivicTrack",
        ),
        "base_url": base_url,

    }

    for value in (
        config["host"],
        config["username"],
        config["password"],
        config["sender"],
        config["sender_name"],
    ):

        if "\r" in value or "\n" in value:
            raise RuntimeError("Invalid email configuration.")

    if "@" not in config["sender"]:
        raise RuntimeError("SMTP_FROM must be an email address.")

    return config


# =====================================================
# GENERAL EMAIL DELIVERY
# =====================================================

def send_email(
    recipient,
    subject,
    text_body,
    html_body=None,
):

    config = get_email_config()

    if (
        not isinstance(recipient, str)
        or not recipient.strip()
        or "@" not in recipient
        or "\r" in recipient
        or "\n" in recipient
    ):
        raise ValueError("Invalid recipient email address.")

    if not isinstance(subject, str) or not subject.strip():
        raise ValueError("Email subject is required.")

    if "\r" in subject or "\n" in subject:
        raise ValueError("Invalid email subject.")

    if not isinstance(text_body, str):
        raise ValueError("Email body must be text.")

    if html_body is not None and not isinstance(html_body, str):
        raise ValueError("HTML email body must be text.")

    message = EmailMessage()

    message["From"] = formataddr((
        config["sender_name"],
        config["sender"],
    ))

    message["To"] = recipient.strip()

    message["Subject"] = subject

    message.set_content(text_body)

    if html_body is not None:

        message.add_alternative(
            html_body,
            subtype="html",
        )

    context = ssl.create_default_context()

    try:

        if config["port"] == 465:

            with smtplib.SMTP_SSL(
                config["host"],
                config["port"],
                timeout=20,
                context=context,
            ) as server:

                server.login(
                    config["username"],
                    config["password"],
                )

                server.send_message(message)

        else:

            with smtplib.SMTP(
                config["host"],
                config["port"],
                timeout=20,
            ) as server:

                server.ehlo()

                server.starttls(context=context)

                server.ehlo()

                server.login(
                    config["username"],
                    config["password"],
                )

                server.send_message(message)

    except (OSError, smtplib.SMTPException) as error:

        # Do not expose provider credentials or raw SMTP details.
        raise RuntimeError(
            "Email delivery failed. Check the SMTP configuration."
        ) from error

    return True


# =====================================================
# EMAIL VERIFICATION
# =====================================================

def send_verification_email(
    recipient,
    full_name,
    token,
):

    if not isinstance(token, str) or not token:
        raise ValueError("Invalid verification token.")

    if not isinstance(full_name, str):
        full_name = "Citizen"

    config = get_email_config()

    verification_url = (
        config["base_url"]
        + "/templates/verify_email.html#token="
        + quote(token, safe="")
    )

    safe_name = escape(full_name)

    safe_url = escape(
        verification_url,
        quote=True,
    )

    subject = "Verify your CivicTrack email address"

    text_body = f"""
Hello {full_name},

Welcome to CivicTrack!

Please open the following link to verify your email address:

{verification_url}

This verification link expires in 30 minutes.

If you did not create this account, you can ignore this email.

CivicTrack Team
"""

    html_body = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify your CivicTrack account</title>
</head>

<body style="
    margin:0;
    padding:35px 15px;
    background:#080f1d;
    color:#eaf2ff;
    font-family:Arial,sans-serif;
">

    <div style="
        max-width:520px;
        margin:auto;
        padding:35px;
        background:#111d30;
        border:1px solid #263750;
        border-radius:16px;
    ">

        <h1 style="color:#60a5fa;">
            CivicTrack
        </h1>

        <h2>Welcome, {safe_name}!</h2>

        <p style="color:#b7c6da;line-height:1.8;">
            Thank you for joining CivicTrack.
            Verify your email address to activate
            your account.
        </p>

        <a
            href="{safe_url}"
            style="
                display:inline-block;
                margin:20px 0;
                padding:14px 24px;
                border-radius:8px;
                background:#2563eb;
                color:white;
                text-decoration:none;
                font-weight:bold;
            "
        >
            Verify Email Address
        </a>

        <p style="color:#9aacbf;font-size:12px;">
            This link expires in 30 minutes and can
            only be used once.
        </p>

        <p style="color:#9aacbf;font-size:12px;">
            If you did not create this account,
            ignore this message.
        </p>

        <hr style="border:1px solid #263750;">

        <p style="color:#71849e;font-size:11px;">
            CivicTrack · Building better communities together.
        </p>

    </div>

</body>
</html>
"""

    return send_email(
        recipient,
        subject,
        text_body,
        html_body,
    )

