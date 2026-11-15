
"""
CivicTrack V3 Authentication Service

Handles:
- Citizen and employee registration
- Secure password hashing
- Login verification
- Session creation and validation
- Session revocation

Google OAuth and email verification are separate integrations.
"""

import hashlib
import hmac
import re
import secrets

from datetime import datetime, timedelta, timezone

from core.database import get_connection


# =====================================================
# SECURITY CONFIGURATION
# =====================================================

SCRYPT_N = 2 ** 17
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_MAXMEM = 256 * 1024 * 1024

PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 128

SESSION_DURATION_DAYS = 7


# =====================================================
# VALIDATION RULES
# =====================================================

USERNAME_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_.-]{2,29}$"
)

EMAIL_PATTERN = re.compile(
    r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
)

ALLOWED_DEPARTMENTS = {
    "Public Works",
    "Electrical",
    "Water Supply",
    "Drainage",
    "Sanitation",
    "General Services",
}


# =====================================================
# PASSWORD HASHING
# =====================================================

def hash_password(password):

    if not isinstance(password, str):
        raise ValueError("Invalid password.")

    if not PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH:
        raise ValueError(
            f"Password must contain between "
            f"{PASSWORD_MIN_LENGTH} and "
            f"{PASSWORD_MAX_LENGTH} characters."
        )

    password_bytes = password.encode("utf-8")

    if len(password_bytes) > 1024:
        raise ValueError("Password is too long.")

    salt = secrets.token_bytes(16)

    password_digest = hashlib.scrypt(
        password_bytes,
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        maxmem=SCRYPT_MAXMEM,
        dklen=64,
    )

    return (
        f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}"
        f"${salt.hex()}${password_digest.hex()}"
    )


# =====================================================
# PASSWORD VERIFICATION
# =====================================================

def verify_password(password, stored_hash):

    if not isinstance(password, str):
        return False

    if not isinstance(stored_hash, str):
        return False

    try:

        (
            algorithm,
            n,
            r,
            p,
            salt_hex,
            digest_hex,
        ) = stored_hash.split("$")

        if algorithm != "scrypt":
            return False

        if (
            int(n) != SCRYPT_N
            or int(r) != SCRYPT_R
            or int(p) != SCRYPT_P
        ):
            return False

        salt = bytes.fromhex(salt_hex)
        expected_digest = bytes.fromhex(digest_hex)

        if len(salt) != 16 or len(expected_digest) != 64:
            return False

        calculated_digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=SCRYPT_N,
            r=SCRYPT_R,
            p=SCRYPT_P,
            maxmem=SCRYPT_MAXMEM,
            dklen=64,
        )

        return hmac.compare_digest(
            calculated_digest,
            expected_digest,
        )

    except (ValueError, TypeError, OverflowError):
        return False


# =====================================================
# PUBLIC USER DATA
# Never expose password hashes or session tokens.
# =====================================================

def public_user(user):

    return {
        "id": user["id"],
        "full_name": user["full_name"],
        "username": user["username"],
        "email": user["email"],
        "role": user["role"],
        "account_status": user["account_status"],
        "email_verified": bool(user["email_verified"]),
        "department": user["department"],
        "created_at": user["created_at"],
    }


# =====================================================
# ACCOUNT REGISTRATION
# =====================================================

def register_account(data):

    if not isinstance(data, dict):
        raise ValueError("Invalid registration data.")

    full_name = data.get("full_name")
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role")

    if not isinstance(full_name, str):
        raise ValueError("Full name is required.")

    full_name = full_name.strip()

    if not 2 <= len(full_name) <= 100:
        raise ValueError("Full name must contain 2-100 characters.")

    if not isinstance(username, str):
        raise ValueError("Username is required.")

    username = username.strip()

    if not USERNAME_PATTERN.fullmatch(username):
        raise ValueError(
            "Username must contain 3-30 characters and use "
            "letters, numbers, dots, underscores or hyphens."
        )

    if not isinstance(email, str):
        raise ValueError("Email address is required.")

    email = email.strip().lower()

    if len(email) > 254 or not EMAIL_PATTERN.fullmatch(email):
        raise ValueError("Enter a valid email address.")

    if role not in ("citizen", "employee"):
        raise ValueError("Invalid account type.")

    department = None

    if role == "employee":

        department = data.get("department")

        if department not in ALLOWED_DEPARTMENTS:
            raise ValueError("Select a valid department.")

    # Never accept an account status from the browser.
    account_status = (
        "pending_approval"
        if role == "employee"
        else "active"
    )

    password_hash = hash_password(password)

    try:

        with get_connection() as connection:

            existing = connection.execute(
                """
                SELECT id
                FROM users
                WHERE email = ?
                   OR username = ? COLLATE NOCASE
                """,
                (email, username),
            ).fetchone()

            if existing:
                raise ValueError(
                    "That email address or username is already registered."
                )

            cursor = connection.execute(
                """
                INSERT INTO users (
                    full_name,
                    email,
                    password_hash,
                    username,
                    role,
                    account_status,
                    email_verified,
                    department
                )
                VALUES (?, ?, ?, ?, ?, ?, 0, ?)
                """,
                (
                    full_name,
                    email,
                    password_hash,
                    username,
                    role,
                    account_status,
                    department,
                ),
            )

            user_id = cursor.lastrowid

            user = connection.execute(
                """
                SELECT *
                FROM users
                WHERE id = ?
                """,
                (user_id,),
            ).fetchone()

            return public_user(user)

    except ValueError:
        raise

    except Exception as error:

        import sqlite3

        if isinstance(error, sqlite3.IntegrityError):
            raise ValueError(
                "That email address or username is already registered."
            ) from error

        raise


# =====================================================
# ACCOUNT LOGIN
# =====================================================

def authenticate_user(identifier, password):

    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("Email or username is required.")

    if not isinstance(password, str) or not password:
        raise ValueError("Password is required.")

    identifier = identifier.strip()

    with get_connection() as connection:

        user = connection.execute(
            """
            SELECT *
            FROM users
            WHERE email = ? COLLATE NOCASE
               OR username = ? COLLATE NOCASE
            """,
            (identifier, identifier),
        ).fetchone()

    if user is None or not verify_password(
        password,
        user["password_hash"],
    ):
        raise ValueError("Invalid email, username or password.")

    if user["account_status"] == "pending_approval":
        raise PermissionError(
            "Your employee account is awaiting administrator approval."
        )

    if user["account_status"] != "active":
        raise PermissionError(
            "Your account is not currently active."
        )

    return public_user(user)


# =====================================================
# SESSION CREATION
# Store only the SHA-256 hash in SQLite.
# =====================================================

def create_session(user_id):

    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("Invalid user ID.")

    raw_token = secrets.token_urlsafe(32)

    token_hash = hashlib.sha256(
        raw_token.encode("utf-8")
    ).hexdigest()

    expires_at = (
        datetime.now(timezone.utc)
        + timedelta(days=SESSION_DURATION_DAYS)
    ).strftime("%Y-%m-%d %H:%M:%S")

    with get_connection() as connection:

        connection.execute(
            """
            DELETE FROM user_sessions
            WHERE expires_at <= CURRENT_TIMESTAMP
            """
        )

        user = connection.execute(
            "SELECT id FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

        if user is None:
            raise ValueError("User does not exist.")

        connection.execute(
            """
            INSERT INTO user_sessions (
                user_id,
                token_hash,
                expires_at
            )
            VALUES (?, ?, ?)
            """,
            (user_id, token_hash, expires_at),
        )

    return raw_token


# =====================================================
# SESSION VALIDATION
# =====================================================

def get_session_user(raw_token):

    if not isinstance(raw_token, str) or not raw_token:
        return None

    if len(raw_token) > 128:
        return None

    token_hash = hashlib.sha256(
        raw_token.encode("utf-8")
    ).hexdigest()

    with get_connection() as connection:

        user = connection.execute(
            """
            SELECT users.*
            FROM user_sessions
            JOIN users
                ON users.id = user_sessions.user_id
            WHERE user_sessions.token_hash = ?
              AND user_sessions.expires_at > CURRENT_TIMESTAMP
            """,
            (token_hash,),
        ).fetchone()

    if user is None:
        return None

    if user["account_status"] != "active":
        return None

    return public_user(user)


# =====================================================
# SESSION LOGOUT
# =====================================================

def revoke_session(raw_token):

    if not isinstance(raw_token, str) or not raw_token:
        return False

    if len(raw_token) > 128:
        return False

    token_hash = hashlib.sha256(
        raw_token.encode("utf-8")
    ).hexdigest()

    with get_connection() as connection:

        cursor = connection.execute(
            """
            DELETE FROM user_sessions
            WHERE token_hash = ?
            """,
            (token_hash,),
        )

        return cursor.rowcount > 0


# =====================================================
# EMAIL VERIFICATION TOKEN GENERATION
# =====================================================

def create_email_verification_token(user_id):

    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("Invalid user ID.")

    raw_token = secrets.token_urlsafe(32)

    token_hash = hashlib.sha256(
        raw_token.encode("utf-8")
    ).hexdigest()

    expires_at = (
        datetime.now(timezone.utc)
        + timedelta(minutes=30)
    ).strftime("%Y-%m-%d %H:%M:%S")

    with get_connection() as connection:

        user = connection.execute(
            """
            SELECT id, email_verified
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()

        if user is None:
            raise ValueError("User does not exist.")

        if user["email_verified"]:
            raise ValueError("Email is already verified.")

        connection.execute(
            """
            DELETE FROM auth_tokens
            WHERE user_id = ?
              AND token_type = 'email_verification'
            """,
            (user_id,),
        )

        connection.execute(
            """
            INSERT INTO auth_tokens (
                user_id,
                token_type,
                token_hash,
                expires_at
            )
            VALUES (?, 'email_verification', ?, ?)
            """,
            (user_id, token_hash, expires_at),
        )

    return raw_token


# =====================================================
# EMAIL VERIFICATION TOKEN VALIDATION
# =====================================================

def verify_email_token(raw_token):

    if not isinstance(raw_token, str):
        return False

    if not 20 <= len(raw_token) <= 128:
        return False

    token_hash = hashlib.sha256(
        raw_token.encode("utf-8")
    ).hexdigest()

    with get_connection() as connection:

        connection.execute("BEGIN IMMEDIATE")

        token = connection.execute(
            """
            SELECT id, user_id
            FROM auth_tokens
            WHERE token_hash = ?
              AND token_type = 'email_verification'
              AND used_at IS NULL
              AND expires_at > CURRENT_TIMESTAMP
            """,
            (token_hash,),
        ).fetchone()

        if token is None:
            return False

        result = connection.execute(
            """
            UPDATE auth_tokens
            SET used_at = CURRENT_TIMESTAMP
            WHERE id = ?
              AND used_at IS NULL
              AND expires_at > CURRENT_TIMESTAMP
            """,
            (token["id"],),
        )

        if result.rowcount != 1:
            return False

        result = connection.execute(
            """
            UPDATE users
            SET email_verified = 1
            WHERE id = ?
            """,
            (token["user_id"],),
        )

        return result.rowcount == 1

