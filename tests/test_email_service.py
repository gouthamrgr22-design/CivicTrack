
import os
import unittest
from unittest.mock import patch, MagicMock

from app.services import email_service


class EmailServiceTests(unittest.TestCase):

    @patch.dict(os.environ, {
        "SMTP_HOST": "smtp.resend.com",
        "SMTP_PORT": "465",
        "SMTP_USERNAME": "resend",
        "SMTP_PASSWORD": "test_secret",
        "SMTP_FROM": "onboarding@resend.dev",
        "CIVICTRACK_BASE_URL": "http://localhost:8000",
    }, clear=True)
    @patch("app.services.email_service.smtplib.SMTP_SSL")
    def test_send_email_uses_ssl(self, mock_smtp):
        server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = server

        email_service.send_email(
            "test@example.com",
            "CivicTrack Test",
            "This is a test email."
        )

        mock_smtp.assert_called_once()
        server.login.assert_called_once_with("resend", "test_secret")
        server.send_message.assert_called_once()

    @patch("app.services.email_service.load_environment")
    @patch.dict(os.environ, {}, clear=True)
    def test_missing_configuration_raises_error(self, mock_load):
        with self.assertRaises(RuntimeError):
            email_service.get_email_config()



if __name__ == "__main__":
    unittest.main()

