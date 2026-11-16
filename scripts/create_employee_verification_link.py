import sys
from pathlib import Path
from urllib.parse import quote

APP_DIR = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP_DIR))

from core.database import initialize_database, get_connection
from services.auth_service import create_email_verification_token


def main():
    initialize_database()

    print("\n=== CIVICTRACK EMPLOYEE EMAIL VERIFICATION ===\n")

    with get_connection() as connection:
        employees = connection.execute(
            """
            SELECT id, full_name, username, email,
                   account_status, email_verified
            FROM users
            WHERE role = 'employee'
            ORDER BY id DESC
            """
        ).fetchall()

    if not employees:
        print("No employee accounts found.")
        return

    print("REGISTERED EMPLOYEE ACCOUNTS\n")

    for employee in employees:
        print(
            f"ID: {employee['id']} | "
            f"Username: {employee['username']} | "
            f"Status: {employee['account_status']} | "
            f"Verified: {bool(employee['email_verified'])}"
        )

    username = input("\nEnter the NEW employee username: ").strip()

    employee = next(
        (item for item in employees if item["username"] == username),
        None,
    )

    if employee is None:
        print("Employee account not found.")
        return

    if employee["email_verified"]:
        print("This employee email is already verified.")
        return

    token = create_email_verification_token(employee["id"])

    url = (
        "http://127.0.0.1:8000/templates/verify_email.html#token="
        + quote(token, safe="")
    )

    print("\nEMPLOYEE VERIFICATION LINK")
    print("==========================")
    print(url)
    print("\nOpen this link in Firefox.")
    print("The link expires in 30 minutes and works once.")

    print("\nAccount approval status:", employee["account_status"])


if __name__ == "__main__":
    main()
