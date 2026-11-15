
"""
CivicTrack V3 — Main HTTP Server

Includes:
- Citizen and employee authentication APIs
- Administrator authentication and dashboard APIs
- Employee approval and rejection
- Email verification and verification-email delivery
- Secure HTTP-only session cookies
- Authenticated employee dashboard APIs
- Existing complaint and tracking APIs
"""

import json
import os

from http.cookies import SimpleCookie
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from core.database import (
    DATABASE_PATH,
    initialize_database,
)

from services.auth_service import (
    register_account,
    authenticate_user,
    create_session,
    get_session_user,
    revoke_session,
    create_email_verification_token,
    verify_email_token,
)

from services.email_service import (
    send_verification_email,
)

from services.complaint_service import (
    submit_complaint,
    list_complaints,
    get_dashboard_statistics,
    get_employee_data,
    get_employee_history,
    employee_action,
    get_public_tracking,
)

from services.admin_service import (
    get_admin_overview,
    decide_employee_account,
)


HOST = "127.0.0.1"
PORT = 8000

APP_DIR = Path(__file__).resolve().parent

MAX_REQUEST_SIZE = 16384
SESSION_COOKIE_NAME = "civictrack_session"


class CivicTrackHandler(SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):

        super().__init__(
            *args,
            directory=str(APP_DIR),
            **kwargs,
        )


    # ==========================================
    # JSON RESPONSE
    # ==========================================

    def send_json(self, status, data, headers=None):

        body = json.dumps(data).encode("utf-8")

        self.send_response(status)

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )

        self.send_header(
            "Content-Length",
            str(len(body)),
        )

        self.send_header("Cache-Control", "no-store")

        for name, value in (headers or {}).items():

            self.send_header(name, value)

        self.end_headers()

        self.wfile.write(body)


    # ==========================================
    # JSON REQUEST READER
    # ==========================================

    def read_json(self):

        try:

            length = int(
                self.headers.get("Content-Length", "0")
            )

        except ValueError:

            raise ValueError("Invalid request length.")

        if length <= 0 or length > MAX_REQUEST_SIZE:

            raise ValueError("Invalid or oversized request.")

        try:

            data = json.loads(
                self.rfile.read(length).decode("utf-8")
            )

        except (UnicodeDecodeError, json.JSONDecodeError):

            raise ValueError("Invalid JSON.")

        if not isinstance(data, dict):

            raise ValueError("JSON body must be an object.")

        return data


    # ==========================================
    # SESSION COOKIE
    # ==========================================

    def get_session_token(self):

        cookie = SimpleCookie()

        try:

            cookie.load(
                self.headers.get("Cookie", "")
            )

        except Exception:

            return None

        morsel = cookie.get(SESSION_COOKIE_NAME)

        return morsel.value if morsel else None


    def build_session_cookie(self, token, max_age=604800):

        cookie = SimpleCookie()

        cookie[SESSION_COOKIE_NAME] = token

        morsel = cookie[SESSION_COOKIE_NAME]

        morsel["httponly"] = True
        morsel["samesite"] = "Lax"
        morsel["path"] = "/"
        morsel["max-age"] = str(max_age)

        # Enable Secure cookies when deployed over HTTPS.
        if os.environ.get("CIVICTRACK_HTTPS") == "1":

            morsel["secure"] = True

        return cookie.output(header="").strip()


    # ==========================================
    # AUTHENTICATED USER
    # ==========================================

    def get_authenticated_user(self):

        return get_session_user(
            self.get_session_token()
        )


    # ==========================================
    # EMPLOYEE ACCESS CONTROL
    # ==========================================

    def require_employee_user(self):

        user = self.get_authenticated_user()

        if user is None:

            self.send_json(
                401,
                {"error": "Please sign in first."},
            )

            return None

        if user["role"] not in ("employee", "admin"):

            self.send_json(
                403,
                {"error": "Employee access required."},
            )

            return None

        return user


    # ==========================================
    # ADMINISTRATOR ACCESS CONTROL
    # ==========================================

    def require_admin_user(self):

        user = self.get_authenticated_user()

        if user is None:

            self.send_json(
                401,
                {"error": "Please sign in first."},
            )

            return None

        if user["role"] != "admin":

            self.send_json(
                403,
                {"error": "Administrator access required."},
            )

            return None

        return user


    # ==========================================
    # STATIC FILE PATH SECURITY
    # ==========================================

    def translate_path(self, path):

        url_path = unquote(
            urlsplit(path).path
        )

        if url_path == "/":

            url_path = "/templates/index.html"

        elif url_path == "/employee":

            url_path = "/templates/employee_dashboard.html"

        elif url_path == "/admin":

            url_path = "/templates/admin_dashboard.html"

        requested = (
            APP_DIR / url_path.lstrip("/")
        ).resolve()

        allowed = [

            (APP_DIR / "templates").resolve(),

            (APP_DIR / "static").resolve(),

        ]

        if not any(
            requested.is_relative_to(folder)
            for folder in allowed
        ):

            return str(APP_DIR / "__not_found__")

        return str(requested)


    def list_directory(self, path):

        self.send_error(
            403,
            "Directory listing disabled",
        )

        return None


    # ==========================================
    # GET REQUESTS
    # ==========================================

    def do_GET(self):

        path = urlsplit(self.path).path


        # ======================================
        # FAVICON
        # ======================================

        if path == "/favicon.ico":

            self.send_response(204)
            self.end_headers()

            return


        # ======================================
        # AUTHENTICATION: CURRENT USER
        # ======================================

        if path == "/api/auth/me":

            try:

                user = self.get_authenticated_user()

                if user is None:

                    self.send_json(
                        401,
                        {"error": "Not authenticated."},
                    )

                else:

                    self.send_json(
                        200,
                        {"user": user},
                    )

            except Exception:

                self.log_error("Session lookup error")

                self.send_json(
                    500,
                    {"error": "Could not check authentication."},
                )

            return


        # ======================================
        # ADMIN DASHBOARD PAGE
        # Only administrators can access it.
        # ======================================

        if path in (
            "/admin",
            "/templates/admin_dashboard.html",
        ):

            try:

                user = self.get_authenticated_user()

                if user is None:

                    self.send_response(302)

                    self.send_header(
                        "Location",
                        "/templates/login.html",
                    )

                    self.send_header("Cache-Control", "no-store")

                    self.end_headers()

                    return

                if user["role"] != "admin":

                    self.send_json(
                        403,
                        {"error": "Administrator access required."},
                    )

                    return

                self.path = "/templates/admin_dashboard.html"

                super().do_GET()

            except Exception:

                self.log_error("Admin page authentication error")

                self.send_json(
                    500,
                    {"error": "Could not verify administrator access."},
                )

            return


        # ======================================
        # ADMIN DASHBOARD OVERVIEW API
        # ======================================

        if path == "/api/admin/overview":

            user = self.require_admin_user()

            if user is None:
                return

            try:

                overview = get_admin_overview()

                self.send_json(
                    200,
                    overview,
                )

            except Exception:

                self.log_error("Admin overview error")

                self.send_json(
                    500,
                    {"error": "Could not load administrator dashboard."},
                )

            return


        # ======================================
        # EMPLOYEE DASHBOARD PAGE
        # ======================================

        if path in (
            "/employee",
            "/templates/employee_dashboard.html",
        ):

            try:

                user = self.get_authenticated_user()

                if user is None:

                    self.send_response(302)

                    self.send_header(
                        "Location",
                        "/templates/login.html",
                    )

                    self.send_header("Cache-Control", "no-store")

                    self.end_headers()

                    return

                if user["role"] not in ("employee", "admin"):

                    self.send_json(
                        403,
                        {"error": "Employee access required."},
                    )

                    return

                self.path = "/templates/employee_dashboard.html"

                super().do_GET()

            except Exception:

                self.log_error("Employee page authentication error")

                self.send_json(
                    500,
                    {"error": "Could not verify employee access."},
                )

            return


        # ======================================
        # CITIZEN COMPLAINT API
        # ======================================

        if path == "/api/complaints":

            try:

                self.send_json(
                    200,
                    {
                        "complaints": list_complaints(),

                        "statistics": get_dashboard_statistics(),
                    },
                )

            except Exception:

                self.log_error("Could not retrieve complaints")

                self.send_json(
                    500,
                    {"error": "Database error."},
                )

            return


        # ======================================
        # PUBLIC COMPLAINT TRACKING
        # ======================================

        parts = path.strip("/").split("/")

        if (
            len(parts) == 4
            and parts[:2] == ["api", "complaints"]
            and parts[3] == "tracking"
        ):

            try:

                reference = unquote(parts[2])

                tracking = get_public_tracking(reference)

                if tracking is None:

                    self.send_json(
                        404,
                        {"error": "Complaint not found."},
                    )

                else:

                    self.send_json(
                        200,
                        tracking,
                    )

            except Exception:

                self.log_error("Citizen tracking error")

                self.send_json(
                    500,
                    {"error": "Could not retrieve tracking history."},
                )

            return


        # ======================================
        # EMPLOYEE DASHBOARD API
        # ======================================

        if path == "/api/employee/complaints":

            user = self.require_employee_user()

            if user is None:
                return

            try:

                department = (
                    "ALL"
                    if user["role"] == "admin"
                    else user["department"]
                )

                result = get_employee_data(department)

                result["employee"] = {

                    "name": user["full_name"],

                    "department": department,

                }

                self.send_json(
                    200,
                    result,
                )

            except Exception:

                self.log_error("Employee dashboard error")

                self.send_json(
                    500,
                    {"error": "Could not load dashboard."},
                )

            return


        # ======================================
        # EMPLOYEE COMPLAINT HISTORY API
        # ======================================

        if (
            len(parts) == 5
            and parts[:3] == ["api", "employee", "complaints"]
            and parts[4] == "updates"
        ):

            user = self.require_employee_user()

            if user is None:
                return

            try:

                complaint_id = int(parts[3])

                department = (
                    "ALL"
                    if user["role"] == "admin"
                    else user["department"]
                )

                updates = get_employee_history(
                    complaint_id,
                    department,
                )

                self.send_json(
                    200,
                    {"updates": updates},
                )

            except ValueError:

                self.send_json(
                    400,
                    {"error": "Invalid complaint ID."},
                )

            except LookupError as error:

                self.send_json(
                    404,
                    {"error": str(error)},
                )

            except Exception:

                self.log_error("Complaint history error")

                self.send_json(
                    500,
                    {"error": "Could not load history."},
                )

            return


        # ======================================
        # UNKNOWN API ENDPOINTS
        # ======================================

        if path.startswith("/api/"):

            self.send_json(
                404,
                {"error": "API endpoint not found."},
            )

            return


        # ======================================
        # OTHER WEBSITE RESOURCES
        # ======================================

        self.path = path

        super().do_GET()


    # ==========================================
    # POST REQUESTS
    # ==========================================

    def do_POST(self):

        path = urlsplit(self.path).path


        # ======================================
        # ACCOUNT LOGOUT
        # Does not require a JSON request body.
        # ======================================

        if path == "/api/auth/logout":

            try:

                token = self.get_session_token()

                if token:

                    revoke_session(token)

                self.send_json(
                    200,
                    {"message": "Logged out successfully."},
                    headers={
                        "Set-Cookie": self.build_session_cookie("", 0)
                    },
                )

            except Exception:

                self.log_error("Logout error")

                self.send_json(
                    500,
                    {"error": "Could not complete logout."},
                )

            return


        # ======================================
        # READ JSON REQUEST
        # ======================================

        try:

            data = self.read_json()

        except ValueError as error:

            self.send_json(
                400,
                {"error": str(error)},
            )

            return


        # ======================================
        # EMAIL VERIFICATION
        # ======================================

        if path == "/api/auth/verify-email":

            try:

                token = data.get("token")

                verified = verify_email_token(token)

                if not verified:

                    self.send_json(
                        400,
                        {
                            "error": (
                                "Verification link is invalid, "
                                "expired, or already used."
                            )
                        },
                    )

                    return

                self.send_json(
                    200,
                    {
                        "message": (
                            "Email verified successfully. "
                            "You can now sign in."
                        )
                    },
                )

            except Exception:

                self.log_error("Email verification error")

                self.send_json(
                    500,
                    {"error": "Could not verify email address."},
                )

            return


        # ======================================
        # ADMIN EMPLOYEE APPROVAL API
        # Only administrators can approve or
        # reject employee registrations.
        # ======================================

        parts = path.strip("/").split("/")

        if (
            len(parts) == 5
            and parts[:3] == ["api", "admin", "employees"]
            and parts[4] == "decision"
        ):

            user = self.require_admin_user()

            if user is None:
                return

            try:

                employee_id = int(parts[3])

                action = data.get("action")

                result = decide_employee_account(
                    employee_id,
                    action,
                )

                self.send_json(
                    200,
                    {
                        "message": (
                            "Employee account "
                            + result["account_status"]
                            + " successfully."
                        ),
                        "result": result,
                    },
                )

            except ValueError as error:

                self.send_json(
                    400,
                    {"error": str(error)},
                )

            except LookupError as error:

                self.send_json(
                    404,
                    {"error": str(error)},
                )

            except Exception:

                self.log_error("Admin employee decision error")

                self.send_json(
                    500,
                    {"error": "Could not update employee account."},
                )

            return


        # ======================================
        # CITIZEN / EMPLOYEE REGISTRATION
        # ======================================

        if path == "/api/auth/register":

            # First, create the account.
            # Account creation is independent of email delivery.

            try:

                user = register_account(data)

            except ValueError as error:

                self.send_json(
                    400,
                    {"error": str(error)},
                )

                return

            except Exception:

                self.log_error("Account registration error")

                self.send_json(
                    500,
                    {"error": "Could not create account."},
                )

                return


            # Next, generate a verification token
            # and send the verification email.

            try:

                verification_token = create_email_verification_token(
                    user["id"]
                )

                send_verification_email(
                    user["email"],
                    user["full_name"],
                    verification_token,
                )

            except Exception:

                self.log_error(
                    "Verification email delivery error"
                )

                self.send_json(
                    503,
                    {
                        "error": (
                            "Your account was created, but we could "
                            "not send the verification email. "
                            "Please try again later."
                        ),

                        "account_created": True,
                    },
                )

                return


            # Registration and email delivery succeeded.

            self.send_json(
                201,
                {
                    "message": (
                        "Account created successfully. "
                        "Check your inbox for the verification link "
                        "before signing in."
                    ),

                    "user": user,
                },
            )

            return


        # ======================================
        # ACCOUNT LOGIN
        # ======================================

        if path == "/api/auth/login":

            try:

                user = authenticate_user(
                    data.get("identifier"),
                    data.get("password"),
                )

                # Email verification is required before sessions.
                if not user["email_verified"]:

                    raise PermissionError(
                        "Please verify your email address before signing in."
                    )

                token = create_session(user["id"])

                self.send_json(
                    200,
                    {
                        "message": "Login successful.",

                        "user": user,
                    },
                    headers={
                        "Set-Cookie": self.build_session_cookie(token)
                    },
                )

            except PermissionError as error:

                self.send_json(
                    403,
                    {"error": str(error)},
                )

            except ValueError:

                self.send_json(
                    401,
                    {
                        "error": "Invalid email, username or password."
                    },
                )

            except Exception:

                self.log_error("Login error")

                self.send_json(
                    500,
                    {"error": "Could not process login."},
                )

            return


        # ======================================
        # CITIZEN COMPLAINT SUBMISSION
        # Authentication ownership will be added
        # in the next complaint integration phase.
        # ======================================

        if path == "/api/complaints":

            try:

                complaint = submit_complaint(data)

                self.send_json(
                    201,
                    {"complaint": complaint},
                )

            except ValueError as error:

                self.send_json(
                    400,
                    {"error": str(error)},
                )

            except Exception:

                self.log_error("Complaint creation error")

                self.send_json(
                    500,
                    {"error": "Could not save complaint."},
                )

            return


        # ======================================
        # EMPLOYEE ACTION
        # Requires an authenticated employee.
        # ======================================

        if (
            len(parts) == 5
            and parts[:3] == ["api", "employee", "complaints"]
            and parts[4] == "action"
        ):

            user = self.require_employee_user()

            if user is None:
                return

            try:

                complaint_id = int(parts[3])

                action = data.get("action")

                message = data.get("message", "")

                department = (
                    "ALL"
                    if user["role"] == "admin"
                    else user["department"]
                )

                result = employee_action(
                    complaint_id,
                    action,
                    user["full_name"],
                    department,
                    message,
                )

                self.send_json(
                    200,
                    {"complaint": result},
                )

            except ValueError as error:

                self.send_json(
                    400,
                    {"error": str(error)},
                )

            except LookupError as error:

                self.send_json(
                    404,
                    {"error": str(error)},
                )

            except PermissionError as error:

                self.send_json(
                    403,
                    {"error": str(error)},
                )

            except Exception:

                self.log_error("Employee action error")

                self.send_json(
                    500,
                    {"error": "Could not process action."},
                )

            return


        # ======================================
        # UNKNOWN POST ENDPOINT
        # ======================================

        self.send_json(
            404,
            {"error": "Endpoint not found."},
        )


# ==========================================
# SERVER STARTUP
# ==========================================

def main():

    initialize_database()

    server = ThreadingHTTPServer(
        (HOST, PORT),
        CivicTrackHandler,
    )

    print()
    print("======================================")
    print("          CIVICTRACK V3")
    print("       AUTHENTICATION BACKEND")
    print("======================================")
    print()
    print(f"Citizen website: http://{HOST}:{PORT}/")
    print(f"Login page: http://{HOST}:{PORT}/templates/login.html")
    print(f"Employee dashboard: http://{HOST}:{PORT}/employee")
    print(f"Admin dashboard: http://{HOST}:{PORT}/admin")
    print(f"Database: {DATABASE_PATH}")
    print()
    print("Authentication APIs:")
    print("POST /api/auth/register")
    print("POST /api/auth/verify-email")
    print("POST /api/auth/login")
    print("GET  /api/auth/me")
    print("POST /api/auth/logout")
    print()
    print("Administrator APIs:")
    print("GET  /api/admin/overview")
    print("POST /api/admin/employees/{id}/decision")
    print()
    print("Press Ctrl+C to stop.")

    try:

        server.serve_forever()

    except KeyboardInterrupt:

        print("\nShutting down...")

    finally:

        server.server_close()


if __name__ == "__main__":

    main()

