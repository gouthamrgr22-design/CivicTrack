
from app.services.email_service import send_email


recipient = input("Enter your Resend account email address: ").strip()

if not recipient or "@" not in recipient:
    raise SystemExit("Please enter a valid email address.")

try:
    send_email(
        recipient=recipient,
        subject="CivicTrack V3 - Email Delivery Test",
        text_body=(
            "Hello!\n\n"
            "This is the first real email delivery test "
            "from CivicTrack V3.\n\n"
            "Resend API integration is being tested.\n\n"
            "CivicTrack Development Team"
        ),
    )

    print("\nEmail sent successfully!")

except Exception as error:
    print(f"\nEmail delivery failed: {error}")
