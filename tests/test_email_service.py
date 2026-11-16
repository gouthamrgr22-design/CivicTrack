
import json
import os
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from app.services import email_service


class EmailServiceTests(unittest.TestCase):

    CONFIG = {
        "RESEND_API_KEY": "re_test_secret",
        "RESEND_FROM": "CivicTrack <onboarding@resend.dev>",
        "CIVICTRACK_BASE_URL": "http://localhost:8000",
    }

    @patch.dict(os.environ, CONFIG, clear=True)
    @patch("app.services.email_service.urllib.request.urlopen")
    def test_send_email_uses_resend_api(self, mock_urlopen):
        response = MagicMock()
        response.status = 200
        response.read.return_value = b'{"id":"email_test_123"}'
        response.__enter__.return_value = response
        mock_urlopen.return_value = response

        result = email_service.send_email(
            "test@example.com",
            "CivicTrack Test",
            "This is a test email.",
            "<p>This is a test email.</p>",
            idempotency_key="test-email-123",
        )

        self.assertEqual(result, "email_test_123")
        mock_urlopen.assert_called_once()

        request = mock_urlopen.call_args.args[0]

        self.assertEqual(request.full_url, email_service.RESEND_API_URL)
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(mock_urlopen.call_args.kwargs["timeout"], 20)

        headers = {
            key.lower(): value
            for key, value in request.header_items()
        }

        self.assertEqual(headers["authorization"], "Bearer re_test_secret")
        self.assertEqual(headers["idempotency-key"], "test-email-123")

        payload = json.loads(request.data.decode("utf-8"))

        self.assertEqual(payload["to"], ["test@example.com"])
        self.assertEqual(payload["subject"], "CivicTrack Test")
        self.assertEqual(payload["text"], "This is a test email.")
        self.assertEqual(payload["html"], "<p>This is a test email.</p>")

    @patch.dict(os.environ, CONFIG, clear=True)
    @patch("app.services.email_service.urllib.request.urlopen")
    def test_verification_email_uses_resend(self, mock_urlopen):
        response = MagicMock()
        response.status = 200
        response.read.return_value = b'{"id":"verification_123"}'
        response.__enter__.return_value = response
        mock_urlopen.return_value = response

        result = email_service.send_verification_email(
            "test@example.com",
            "Test Citizen",
            "verification-token-123",
        )

        self.assertEqual(result, "verification_123")

        request = mock_urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))

        self.assertIn("verification-token-123", payload["text"])
        self.assertIn("verify_email.html#token=", payload["text"])
        self.assertIn("verification-token-123", payload["html"])

    @patch.dict(os.environ, CONFIG, clear=True)
    @patch("app.services.email_service.urllib.request.urlopen")
    def test_resend_http_error_is_handled(self, mock_urlopen):
        mock_urlopen.side_effect = HTTPError(
            email_service.RESEND_API_URL,
            422,
            "Invalid request",
            None,
            None,
        )

        with self.assertRaisesRegex(RuntimeError, "Resend rejected"):
            email_service.send_email(
                "test@example.com",
                "Test",
                "Test body",
            )

    @patch("app.services.email_service.load_environment")
    @patch.dict(os.environ, {}, clear=True)
    def test_missing_configuration_raises_error(self, mock_load):
        with self.assertRaises(RuntimeError):
            email_service.get_email_config()


if __name__ == "__main__":
    unittest.main()

