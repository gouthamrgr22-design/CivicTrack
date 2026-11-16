import sys
from pathlib import Path
from urllib.parse import quote

APP_DIR = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP_DIR))

from core.database import initialize_database, get_connection
from services.auth_service import create_email_verification_token


def main():
    initialize_database()

    with get_connection() as connection:
        admin = connection.execute(
            """
            SELECT id, username, email, email_verified
            FROM users
            WHERE username = 'goutham_admin'
              AND role = 'admin'
            """
        ).fetchone()

    if admin is None:
        print("Administrator account not found.")
        return

    if admin["email_verified"]:
        print("Administrator email is already verified.")
        return

    token = create_email_verification_token(admin["id"])

    url = (
        "http://localhost:8000/templates/verify_email.html#token="
        + quote(token, safe="")
    )

    print("\nADMIN VERIFICATION LINK")
    print("=======================")
    print(url)
    print("\nOpen this link in your browser.")
    print("The link expires in 30 minutes and works once.")


if __name__ == "__main__":
    main()
