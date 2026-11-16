import re
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP_DIR))

from core.database import get_connection, initialize_database
from services.auth_service import create_email_verification_token
from services.email_service import send_verification_email


def main():
    initialize_database()

    print("\n=== CIVICTRACK ADMIN EMAIL UPDATE ===")

    new_email = input("New admin email: ").strip().lower()

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", new_email):
        print("Invalid email address.")
        return

    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")

        admin = connection.execute(
            """
            SELECT id, full_name, email
            FROM users
            WHERE username = 'goutham_admin'
              AND role = 'admin'
            """
        ).fetchone()

        if admin is None:
            print("Administrator account not found.")
            return

        duplicate = connection.execute(
            """
            SELECT id FROM users
            WHERE email = ? COLLATE NOCASE
              AND id != ?
            """,
            (new_email, admin["id"]),
        ).fetchone()

        if duplicate:
            print("This email belongs to another account.")
            return

        connection.execute(
            """
            UPDATE users
            SET email = ?,
                email_verified = 0
            WHERE id = ?
            """,
            (new_email, admin["id"]),
        )

    try:
        token = create_email_verification_token(admin["id"])

        send_verification_email(
            new_email,
            admin["full_name"],
            token,
        )

        print("\nAdmin email updated successfully.")
        print("Verification email sent.")
        print("Check your inbox.")

    except Exception as error:
        print("\nEmail updated, but delivery failed.")
        print("Error:", error)


if __name__ == "__main__":
    main()
