#!/usr/bin/env python3

import re
import sys
from getpass import getpass
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP_DIR))

from core.database import get_connection, initialize_database
from services.auth_service import hash_password, create_email_verification_token
from services.email_service import send_verification_email


def main():
    print("\n=== CIVICTRACK FIRST ADMIN SETUP ===\n")

    initialize_database()

    full_name = input("Admin full name: ").strip()
    username = input("Admin username: ").strip()
    email = input("Admin email: ").strip().lower()

    if not full_name:
        print("Name is required.")
        return

    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{2,29}", username):
        print("Invalid username.")
        return

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        print("Invalid email.")
        return

    password = getpass("Admin password: ")
    confirmation = getpass("Confirm password: ")

    if password != confirmation:
        print("Passwords do not match.")
        return

    try:
        password_hash = hash_password(password)
    except ValueError as error:
        print(error)
        return

    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")

        admin = connection.execute(
            "SELECT id FROM users WHERE role = 'admin' LIMIT 1"
        ).fetchone()

        if admin:
            print("An administrator already exists.")
            return

        existing = connection.execute(
            """
            SELECT id FROM users
            WHERE email = ? COLLATE NOCASE
               OR username = ? COLLATE NOCASE
            """,
            (email, username),
        ).fetchone()

        if existing:
            print("Email or username already exists.")
            return

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
            VALUES (?, ?, ?, ?, 'admin', 'active', 0, NULL)
            """,
            (full_name, email, password_hash, username),
        )

        admin_id = cursor.lastrowid

    try:
        token = create_email_verification_token(admin_id)
        send_verification_email(email, full_name, token)

        print("\nAdministrator created successfully.")
        print("Verification email sent.")
        print("Verify your email before logging in.")

    except Exception as error:
        print("\nAdministrator was created, but email delivery failed.")
        print("Contact the project administrator to recover verification.")
        print(f"Error: {error}")


if __name__ == "__main__":
    main()
