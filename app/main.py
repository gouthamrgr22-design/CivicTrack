
"""
CivicTrack employee dashboard and complaint API.
"""

import json

from http.server import (
    SimpleHTTPRequestHandler,
    ThreadingHTTPServer,
)

from pathlib import Path
from urllib.parse import unquote, urlsplit

from core.database import (
    DATABASE_PATH,
    initialize_database,
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


HOST = "127.0.0.1"
PORT = 8000

APP_DIR = Path(__file__).resolve().parent

MAX_REQUEST_SIZE = 16384

# Temporary local demonstration identity.
# Replace with authenticated employee sessions before deployment.
EMPLOYEE_NAME = "GCEM FACULTIES"
EMPLOYEE_DEPARTMENT = "ALL"


class CivicTrackHandler(SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            directory=str(APP_DIR),
            **kwargs,
        )

    def send_json(self, status, data):

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

        self.end_headers()

        self.wfile.write(body)

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


    def translate_path(self, path):

        url_path = unquote(urlsplit(path).path)

        # Citizen homepage.
        if url_path == "/":
            url_path = "/templates/index.html"

        # Employee dashboard.
        elif url_path == "/employee":
            url_path = "/templates/employee_dashboard.html"

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

    def do_GET(self):

        path = urlsplit(self.path).path

        if path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return

        # Employee homepage shortcut.

        if path == "/employee":
            self.path = "/templates/employee_dashboard.html"
            super().do_GET()
            return

        # Citizen complaint API.

        if path == "/api/complaints":

            try:
                self.send_json(200, {
                    "complaints": list_complaints(),
                    "statistics": get_dashboard_statistics(),
                })
            except Exception:
                self.log_error("Could not retrieve complaints")
                self.send_json(500, {"error": "Database error."})

            return

        # Citizen complaint tracking API.

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

                    self.send_json(200, tracking)

            except Exception:

                self.log_error("Citizen tracking error")

                self.send_json(
                    500,
                    {"error": "Could not retrieve tracking history."},
                )

            return


        # Employee dashboard API.

        if path == "/api/employee/complaints":

            try:
                result = get_employee_data(
                    EMPLOYEE_DEPARTMENT
                )

                result["employee"] = {
                    "name": EMPLOYEE_NAME,
                    "department": EMPLOYEE_DEPARTMENT,
                }

                self.send_json(200, result)

            except Exception:
                self.log_error("Employee dashboard error")
                self.send_json(500, {"error": "Could not load dashboard."})

            return

        # Employee complaint history API.

        parts = path.strip("/").split("/")

        if (
            len(parts) == 5
            and parts[:3] == ["api", "employee", "complaints"]
            and parts[4] == "updates"
        ):

            try:

                complaint_id = int(parts[3])

                updates = get_employee_history(
                    complaint_id,
                    EMPLOYEE_DEPARTMENT,
                )

                self.send_json(200, {"updates": updates})

            except ValueError:
                self.send_json(400, {"error": "Invalid complaint ID."})

            except LookupError as error:
                self.send_json(404, {"error": str(error)})

            except Exception:
                self.log_error("Complaint history error")
                self.send_json(500, {"error": "Could not load history."})

            return

        # Other website resources.

        if path.startswith("/api/"):
            self.send_json(404, {"error": "API endpoint not found."})
            return

        self.path = path

        super().do_GET()

    def do_POST(self):

        path = urlsplit(self.path).path

        try:
            data = self.read_json()
        except ValueError as error:
            self.send_json(400, {"error": str(error)})
            return

        # Citizen complaint submission.

        if path == "/api/complaints":

            try:

                complaint = submit_complaint(data)

                self.send_json(
                    201,
                    {"complaint": complaint},
                )

            except ValueError as error:
                self.send_json(400, {"error": str(error)})

            except Exception:
                self.log_error("Complaint creation error")
                self.send_json(500, {"error": "Could not save complaint."})

            return

        # Employee action endpoint.

        parts = path.strip("/").split("/")

        if (
            len(parts) == 5
            and parts[:3] == ["api", "employee", "complaints"]
            and parts[4] == "action"
        ):

            try:

                complaint_id = int(parts[3])

                action = data.get("action")

                message = data.get("message", "")

                result = employee_action(
                    complaint_id,
                    action,
                    EMPLOYEE_NAME,
                    EMPLOYEE_DEPARTMENT,
                    message,
                )

                self.send_json(
                    200,
                    {"complaint": result},
                )

            except ValueError as error:
                self.send_json(400, {"error": str(error)})

            except LookupError as error:
                self.send_json(404, {"error": str(error)})

            except PermissionError as error:
                self.send_json(403, {"error": str(error)})

            except Exception:
                self.log_error("Employee action error")
                self.send_json(500, {"error": "Could not process action."})

            return

        self.send_json(404, {"error": "Endpoint not found."})


def main():

    initialize_database()

    server = ThreadingHTTPServer(
        (HOST, PORT),
        CivicTrackHandler,
    )

    print()
    print("======================================")
    print("       CIVICTRACK EMPLOYEE PORTAL")
    print("======================================")
    print()
    print(f"Citizen website: http://{HOST}:{PORT}/")
    print(f"Employee portal: http://{HOST}:{PORT}/employee")
    print(f"Database: {DATABASE_PATH}")
    print()
    print("Local demo employee:", EMPLOYEE_NAME)
    print("Department:", EMPLOYEE_DEPARTMENT)
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

