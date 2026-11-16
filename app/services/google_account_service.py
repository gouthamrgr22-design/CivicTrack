"""Create or link a CivicTrack account from a verified Google identity."""

import re
import secrets

from core.database import get_connection
from services.auth_service import (
    ALLOWED_DEPARTMENTS,
    hash_password,
    public_user,
)


def _new_username(connection, email):
    local_part = email.split("@", 1)[0].lower()
    base = re.sub(r"[^a-z0-9_.-]+", "-", local_part).strip("._-")
    if not base or not base[0].isalnum():
        base = "google-user"
    base = base[:20]

    for _ in range(20):
        candidate = f"{base}-{secrets.token_hex(3)}"[:30]
        exists = connection.execute(
            "SELECT 1 FROM users WHERE username = ? COLLATE NOCASE",
            (candidate,),
        ).fetchone()
        if not exists:
            return candidate
    raise RuntimeError("Could not allocate a unique username for this Google account.")


def create_or_link_google_user(identity, mode, role, department=None):
    """Return a public user without changing existing roles or approval status."""
    if mode not in ("login", "register"):
        raise ValueError("Invalid Google sign-in mode.")
    if role not in ("citizen", "employee"):
        raise ValueError("Google registration supports citizen or employee accounts only.")

    email = identity["email"]
    subject = identity["sub"]
    authoritative = bool(identity.get("authoritative_email"))

    with get_connection() as connection:
        linked = connection.execute(
            """
            SELECT users.*
            FROM oauth_accounts
            JOIN users ON users.id = oauth_accounts.user_id
            WHERE oauth_accounts.provider = 'google'
              AND oauth_accounts.provider_subject = ?
            """,
            (subject,),
        ).fetchone()

        if linked:
            user = linked
            if user["account_status"] not in ("active", "pending_approval"):
                raise PermissionError("This account is not currently active.")

            # A Google subject can keep the same identity while its primary
            # email changes. Never use the new address to mark the CivicTrack
            # account's old stored email as verified.
            same_stored_email = user["email"].strip().lower() == email
            if authoritative and same_stored_email and not user["email_verified"]:
                connection.execute(
                    "UPDATE users SET email_verified = 1 WHERE id = ?",
                    (user["id"],),
                )
                user = connection.execute(
                    "SELECT * FROM users WHERE id = ?",
                    (user["id"],),
                ).fetchone()

            connection.execute(
                """UPDATE oauth_accounts
                   SET provider_email = ?
                   WHERE provider = 'google' AND provider_subject = ?""",
                (email, subject),
            )
            return public_user(user)

        existing = connection.execute(
            "SELECT * FROM users WHERE email = ? COLLATE NOCASE",
            (email,),
        ).fetchone()

        if existing:
            if existing["account_status"] not in ("active", "pending_approval"):
                raise PermissionError("This account is not currently active.")

            # Never silently link a third-party Google address to an
            # unverified local account. Gmail/Workspace are authoritative.
            if not existing["email_verified"] and not authoritative:
                raise PermissionError(
                    "Verify this email using the CivicTrack email link before linking Google."
                )

            if authoritative and not existing["email_verified"]:
                connection.execute(
                    "UPDATE users SET email_verified = 1 WHERE id = ?",
                    (existing["id"],),
                )

            user_id = existing["id"]

        else:
            if mode != "register":
                raise LookupError(
                    "No CivicTrack account is linked to this Google account. Switch to Create Account to register."
                )

            if role == "employee" and department not in ALLOWED_DEPARTMENTS:
                raise ValueError("Select a valid employee department.")

            full_name = (identity.get("name") or "").strip()[:100]
            if len(full_name) < 2:
                full_name = email.split("@", 1)[0][:100] or "Google user"
            username = _new_username(connection, email)
            password_hash = hash_password(secrets.token_urlsafe(48))
            account_status = "pending_approval" if role == "employee" else "active"
            email_verified = 1 if authoritative else 0
            assigned_department = department if role == "employee" else None

            cursor = connection.execute(
                """
                INSERT INTO users (
                    full_name, email, password_hash, username,
                    role, account_status, email_verified, department
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    full_name,
                    email,
                    password_hash,
                    username,
                    role,
                    account_status,
                    email_verified,
                    assigned_department,
                ),
            )
            user_id = cursor.lastrowid

        # `provider_subject` is Google's stable immutable account identifier.
        connection.execute(
            """
            INSERT INTO oauth_accounts (
                user_id, provider, provider_subject, provider_email
            ) VALUES (?, 'google', ?, ?)
            """,
            (user_id, subject, email),
        )

        user = connection.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

    return public_user(user)
