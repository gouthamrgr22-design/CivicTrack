"""Google Identity Services ID-token verification for CivicTrack V3."""

import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2 import id_token


def load_environment():
    """Load project .env without overriding environment variables."""
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


def get_google_client_id():
    load_environment()
    return os.environ.get("GOOGLE_CLIENT_ID", "").strip()


def verify_google_id_token(raw_token, expected_nonce):
    """Verify signature and Google claims, then return trusted identity data."""
    client_id = get_google_client_id()
    if not client_id:
        raise RuntimeError("Google Sign-In is not configured on this server.")
    if not isinstance(raw_token, str) or not 50 <= len(raw_token) <= 16384:
        raise ValueError("Invalid Google identity token.")
    if not isinstance(expected_nonce, str) or not 16 <= len(expected_nonce) <= 128:
        raise ValueError("Google sign-in session expired. Reload the page and try again.")

    try:
        claims = id_token.verify_oauth2_token(
            raw_token,
            Request(),
            audience=client_id,
        )
    except ValueError as error:
        raise ValueError("Google identity token is invalid or expired.") from error
    except Exception as error:
        raise RuntimeError("Google identity verification is temporarily unavailable.") from error

    if claims.get("iss") not in (
        "accounts.google.com",
        "https://accounts.google.com",
    ):
        raise ValueError("Google identity token issuer is invalid.")

    if claims.get("nonce") != expected_nonce:
        raise ValueError("Google sign-in nonce does not match this browser session.")

    subject = claims.get("sub")
    email = claims.get("email")
    if not isinstance(subject, str) or not subject or len(subject) > 255:
        raise ValueError("Google did not return a valid account identifier.")
    if not isinstance(email, str) or len(email) > 254 or "@" not in email:
        raise ValueError("Google did not return a valid email address.")
    if claims.get("email_verified") is not True:
        raise ValueError("Google has not verified this email address.")

    email = email.strip().lower()
    email_domain = email.rsplit("@", 1)[-1]
    hosted_domain = claims.get("hd")

    # Google is authoritative for @gmail.com and for verified Google
    # Workspace accounts when the signed `hd` claim is present. The hosted
    # domain need not equal an email alias domain.
    authoritative_email = (
        email_domain == "gmail.com"
        or (isinstance(hosted_domain, str) and bool(hosted_domain.strip()))
    )

    return {
        "sub": subject,
        "email": email,
        "email_verified": True,
        "authoritative_email": authoritative_email,
        "name": claims.get("name") if isinstance(claims.get("name"), str) else "",
        "picture": claims.get("picture") if isinstance(claims.get("picture"), str) else "",
    }
