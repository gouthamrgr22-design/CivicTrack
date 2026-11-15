
import hashlib
import tempfile
import unittest

from pathlib import Path

import core.database as database

from services.auth_service import (
    register_account,
    authenticate_user,
    create_session,
    get_session_user,
    revoke_session,
    create_email_verification_token,
    verify_email_token,
)


class AuthenticationTests(unittest.TestCase):

    def setUp(self):

        self.temp_directory = tempfile.TemporaryDirectory()

        self.original_database_path = database.DATABASE_PATH

        database.DATABASE_PATH = (
            Path(self.temp_directory.name) / "test.db"
        )

        database.initialize_database()


    def tearDown(self):

        database.DATABASE_PATH = self.original_database_path

        self.temp_directory.cleanup()


    def create_account(self, role="citizen", username="testuser"):

        return register_account({
            "full_name": "Test User",
            "username": username,
            "email": f"{username}@example.com",
            "password": "Secure-Test-Password-2026!",
            "role": role,
            "department": "Public Works" if role == "employee" else None,
        })


    def test_citizen_registration(self):

        user = self.create_account()

        self.assertEqual(user["role"], "citizen")
        self.assertEqual(user["account_status"], "active")
        self.assertFalse(user["email_verified"])

        self.assertNotIn("password_hash", user)

        print("PASS: Citizen registration")


    def test_employee_requires_approval(self):

        user = self.create_account(
            role="employee",
            username="employee1",
        )

        self.assertEqual(
            user["account_status"],
            "pending_approval",
        )

        with self.assertRaises(PermissionError):

            authenticate_user(
                "employee1",
                "Secure-Test-Password-2026!",
            )

        print("PASS: Employee approval protection")


    def test_administrator_role_cannot_be_self_registered(self):

        with self.assertRaises(ValueError):

            register_account({
                "full_name": "Test Administrator",
                "username": "fakeadmin",
                "email": "admin@example.com",
                "password": "Secure-Test-Password-2026!",
                "role": "admin",
            })

        print("PASS: Administrator privilege protection")


    def test_login_and_session_lifecycle(self):

        user = self.create_account(
            username="sessionuser",
        )

        user_id = user["id"]

        # Simulate successful email verification.
        with database.get_connection() as connection:

            connection.execute(
                """
                UPDATE users
                SET email_verified = 1
                WHERE id = ?
                """,
                (user_id,),
            )

        authenticated = authenticate_user(
            "sessionuser",
            "Secure-Test-Password-2026!",
        )

        self.assertEqual(authenticated["id"], user_id)

        token = create_session(user_id)

        session_user = get_session_user(token)

        self.assertEqual(session_user["id"], user_id)

        # The raw session token must never be stored.
        with database.get_connection() as connection:

            stored_hash = connection.execute(
                """
                SELECT token_hash
                FROM user_sessions
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()["token_hash"]

        self.assertEqual(
            stored_hash,
            hashlib.sha256(token.encode()).hexdigest(),
        )

        self.assertTrue(revoke_session(token))

        self.assertIsNone(get_session_user(token))

        print("PASS: Login and session lifecycle")


    # ==========================================
    # EMAIL VERIFICATION TESTS
    # ==========================================

    def test_email_verification_token_is_single_use(self):

        user = self.create_account(
            username="verifyuser",
        )

        token = create_email_verification_token(user["id"])

        token_hash = hashlib.sha256(
            token.encode("utf-8")
        ).hexdigest()

        with database.get_connection() as connection:

            stored = connection.execute(
                """
                SELECT token_hash, used_at
                FROM auth_tokens
                WHERE user_id = ?
                """,
                (user["id"],),
            ).fetchone()

        self.assertEqual(stored["token_hash"], token_hash)
        self.assertNotEqual(stored["token_hash"], token)

        self.assertTrue(verify_email_token(token))

        with database.get_connection() as connection:

            updated_user = connection.execute(
                """
                SELECT email_verified
                FROM users
                WHERE id = ?
                """,
                (user["id"],),
            ).fetchone()

        self.assertEqual(updated_user["email_verified"], 1)

        # A verification token must never work twice.
        self.assertFalse(verify_email_token(token))

        print("PASS: Email verification and single-use protection")


    def test_invalid_email_verification_token(self):

        self.assertFalse(
            verify_email_token("invalid-verification-token")
        )

        print("PASS: Invalid email verification token rejected")


    def test_expired_email_verification_token(self):

        user = self.create_account(
            username="expireduser",
        )

        token = create_email_verification_token(user["id"])

        token_hash = hashlib.sha256(
            token.encode("utf-8")
        ).hexdigest()

        # Simulate a token that expired in the past.
        with database.get_connection() as connection:

            connection.execute(
                """
                UPDATE auth_tokens
                SET expires_at = '2000-01-01 00:00:00'
                WHERE token_hash = ?
                """,
                (token_hash,),
            )

        self.assertFalse(verify_email_token(token))

        with database.get_connection() as connection:

            account = connection.execute(
                """
                SELECT email_verified
                FROM users
                WHERE id = ?
                """,
                (user["id"],),
            ).fetchone()

        self.assertEqual(account["email_verified"], 0)

        print("PASS: Expired email verification token rejected")


# ==========================================
# DIRECT TEST EXECUTION
# ==========================================

if __name__ == "__main__":
    unittest.main()

