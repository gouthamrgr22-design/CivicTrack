#!/usr/bin/env python3

import sys
from pathlib import Path
from getpass import getpass

APP_DIR = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP_DIR))

from core.database import get_connection, initialize_database
from services.auth_service import hash_password


def main():

    print("\n====================================")
    print("   CIVICTRACK ADMIN PASSWORD RESET")
    print("====================================\n")

    initialize_database()

    password = getpass("New administrator password: ")
    confirmation = getpass("Confirm new password: ")

    if password != confirmation:
        print("\nPasswords do not match.")
        return

    try:
        password_hash = hash_password(password)
    except ValueError as error:
        print(f"\nPassword error: {error}")
        return

    with get_connection() as connection:

        connection.execute("BEGIN IMMEDIATE")

        admin = connection.execute(
            """
            SELECT id
            FROM users
            WHERE username = ?
              AND role = 'admin'
            """,
            ("goutham_admin",),
        ).fetchone()

        if admin is None:
            print("\nAdministrator account not found.")
            return

        connection.execute(
            """
            UPDATE users
            SET password_hash = ?
            WHERE id = ?
            """,
            (password_hash, admin["id"]),
        )

        connection.execute(
            """
            DELETE FROM user_sessions
            WHERE user_id = ?
            """,
            (admin["id"],),
        )

    print("\nPassword reset successfully!")
    print("Administrator email verification is unchanged.")
    print("You can now sign in.")


if __name__ == "__main__":
    main()
