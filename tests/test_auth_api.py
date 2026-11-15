
import json
import tempfile
import threading
import unittest

from unittest.mock import patch
from http.server import ThreadingHTTPServer
from pathlib import Path
from http.cookiejar import CookieJar
from urllib.error import HTTPError
from urllib.request import (
    Request,
    build_opener,
    HTTPCookieProcessor,
)

import core.database as database
import main


class AuthenticationAPITests(unittest.TestCase):

    def setUp(self):

        self.temp_directory = tempfile.TemporaryDirectory()

        self.original_database_path = database.DATABASE_PATH

        database.DATABASE_PATH = (
            Path(self.temp_directory.name) / "api-test.db"
        )

        database.initialize_database()

        # Prevent API tests from sending real emails.
        self.email_delivery_patcher = patch.object(
            main,
            "send_verification_email",
            return_value=True,
        )

        self.mock_send_verification_email = (
            self.email_delivery_patcher.start()
        )

        self.addCleanup(
            self.email_delivery_patcher.stop
        )

        # Start an isolated HTTP server for this test.
        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            main.CivicTrackHandler,
        )

        self.server_thread = threading.Thread(
            target=self.server.serve_forever,
            daemon=True,
        )

        self.server_thread.start()

        self.base_url = (
            f"http://127.0.0.1:{self.server.server_port}"
        )

        self.cookie_jar = CookieJar()

        self.opener = build_opener(
            HTTPCookieProcessor(self.cookie_jar)
        )


    def tearDown(self):

        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join()

        database.DATABASE_PATH = self.original_database_path

        self.temp_directory.cleanup()


    # ==========================================
    # HTTP TEST REQUEST HELPER
    # ==========================================

    def request(self, method, path, payload=None):

        body = None
        headers = {}

        if payload is not None:

            body = json.dumps(payload).encode("utf-8")

            headers["Content-Type"] = "application/json"

        request = Request(
            self.base_url + path,
            data=body,
            headers=headers,
            method=method,
        )

        try:

            with self.opener.open(request) as response:

                return (
                    response.status,
                    json.loads(response.read()),
                    response.headers,
                )

        except HTTPError as error:

            try:

                return (
                    error.code,
                    json.loads(error.read()),
                    error.headers,
                )

            finally:

                error.close()


    # ==========================================
    # CITIZEN REGISTRATION HELPER
    # ==========================================

    def register_citizen(self):

        return self.request(
            "POST",
            "/api/auth/register",
            {
                "full_name": "Test Citizen",
                "username": "citizen_test",
                "email": "citizen@example.com",
                "password": "Secure-Test-Password-2026!",
                "role": "citizen",
            },
        )


    # ==========================================
    # REGISTRATION AND EMAIL VERIFICATION
    # ==========================================

    def test_registration(self):

        status, result, headers = self.register_citizen()

        self.assertEqual(status, 201)

        self.assertEqual(
            result["user"]["role"],
            "citizen",
        )

        self.assertEqual(
            result["user"]["account_status"],
            "active",
        )

        self.assertFalse(
            result["user"]["email_verified"]
        )

        self.assertNotIn(
            "password_hash",
            result["user"],
        )

        # Registration must trigger verification email delivery.
        self.mock_send_verification_email.assert_called_once()

        recipient, full_name, token = (
            self.mock_send_verification_email.call_args[0]
        )

        self.assertEqual(
            recipient,
            "citizen@example.com",
        )

        self.assertEqual(
            full_name,
            "Test Citizen",
        )

        self.assertTrue(token)

        # Verify the email using the actual HTTP API.
        verify_status, verify_result, _ = self.request(
            "POST",
            "/api/auth/verify-email",
            {"token": token},
        )

        self.assertEqual(verify_status, 200)

        self.assertIn(
            "verified",
            verify_result["message"].lower(),
        )

        # A verification token must only work once.
        second_status, second_result, _ = self.request(
            "POST",
            "/api/auth/verify-email",
            {"token": token},
        )

        self.assertEqual(second_status, 400)

        print("PASS: Registration API")
        print("PASS: Verification email generation")
        print("PASS: Email verification API")
        print("PASS: Single-use verification token")


    # ==========================================
    # EMPLOYEE REGISTRATION AND APPROVAL
    # ==========================================

    def test_employee_registration_requires_approval(self):

        status, result, headers = self.request(
            "POST",
            "/api/auth/register",
            {
                "full_name": "Test Employee",
                "username": "employee_test",
                "email": "employee@example.com",
                "password": "Secure-Test-Password-2026!",
                "role": "employee",
                "department": "Public Works",
            },
        )

        self.assertEqual(status, 201)

        self.assertEqual(
            result["user"]["account_status"],
            "pending_approval",
        )

        self.assertFalse(
            result["user"]["email_verified"]
        )

        # Employee registration must also trigger verification email.
        self.mock_send_verification_email.assert_called_once()

        # An unapproved employee cannot log in.
        login_status, login_result, _ = self.request(
            "POST",
            "/api/auth/login",
            {
                "identifier": "employee_test",
                "password": "Secure-Test-Password-2026!",
            },
        )

        self.assertEqual(login_status, 403)

        self.assertIn(
            "approval",
            login_result["error"].lower(),
        )

        print("PASS: Employee registration")
        print("PASS: Employee approval protection")


    # ==========================================
    # UNVERIFIED ACCOUNT LOGIN PROTECTION
    # ==========================================

    def test_unverified_citizen_cannot_login(self):

        status, result, _ = self.register_citizen()

        self.assertEqual(status, 201)

        login_status, login_result, _ = self.request(
            "POST",
            "/api/auth/login",
            {
                "identifier": "citizen_test",
                "password": "Secure-Test-Password-2026!",
            },
        )

        self.assertEqual(login_status, 403)

        self.assertIn(
            "verify",
            login_result["error"].lower(),
        )

        print("PASS: Unverified citizen login rejected")


    # ==========================================
    # LOGIN, SESSION, CURRENT USER AND LOGOUT
    # ==========================================

    def test_login_cookie_me_and_logout(self):

        # Register a citizen.
        status, result, _ = self.register_citizen()

        self.assertEqual(status, 201)

        # Retrieve the token passed to the mocked email service.
        self.mock_send_verification_email.assert_called_once()

        verification_token = (
            self.mock_send_verification_email.call_args[0][2]
        )

        self.assertTrue(verification_token)

        # Verify the email through the real HTTP API.
        verify_status, verify_result, _ = self.request(
            "POST",
            "/api/auth/verify-email",
            {"token": verification_token},
        )

        self.assertEqual(verify_status, 200)

        print("PASS: Email verification before login")

        # Login.
        status, result, headers = self.request(
            "POST",
            "/api/auth/login",
            {
                "identifier": "citizen_test",
                "password": "Secure-Test-Password-2026!",
            },
        )

        self.assertEqual(status, 200)

        self.assertIn(
            "HttpOnly",
            headers.get("Set-Cookie", ""),
        )

        self.assertTrue(
            len(self.cookie_jar) > 0
        )

        print("PASS: Login API and HttpOnly cookie")

        # Current user.
        status, result, _ = self.request(
            "GET",
            "/api/auth/me",
        )

        self.assertEqual(status, 200)

        self.assertEqual(
            result["user"]["username"],
            "citizen_test",
        )

        print("PASS: Current user API")

        # Logout.
        status, result, _ = self.request(
            "POST",
            "/api/auth/logout",
        )

        self.assertEqual(status, 200)

        # Session must be invalid after logout.
        status, result, _ = self.request(
            "GET",
            "/api/auth/me",
        )

        self.assertEqual(status, 401)

        print("PASS: Logout and session invalidation")


    # ==========================================
    # UNAUTHENTICATED ACCESS PROTECTION
    # ==========================================

    def test_current_user_without_login(self):

        status, result, _ = self.request(
            "GET",
            "/api/auth/me",
        )

        self.assertEqual(status, 401)

        print("PASS: Unauthenticated access rejected")


if __name__ == "__main__":

    unittest.main()

