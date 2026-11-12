
"""
CivicTrack v0.1
Local development web server.

Uses only Python's standard library.
"""

from http.server import (
    SimpleHTTPRequestHandler,
    ThreadingHTTPServer,
)
from pathlib import Path
from urllib.parse import unquote, urlsplit


# Application directory.
APP_DIR = Path(__file__).resolve().parent

HOST = "127.0.0.1"
PORT = 8000


class CivicTrackHandler(SimpleHTTPRequestHandler):
    """Serve CivicTrack website files safely."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            directory=str(APP_DIR),
            **kwargs,
        )

    def translate_path(self, path):
        """
        Only allow access to the templates and static directories.
        Prevent access to Python source files and other project data.
        """

        url_path = unquote(urlsplit(path).path)

        if url_path == "/":
            url_path = "/templates/index.html"

        requested_path = (
            APP_DIR / url_path.lstrip("/")
        ).resolve()

        allowed_directories = [
            (APP_DIR / "templates").resolve(),
            (APP_DIR / "static").resolve(),
        ]

        allowed = any(
            requested_path.is_relative_to(directory)
            for directory in allowed_directories
        )

        if not allowed:
            return str(APP_DIR / "__not_found__")

        return str(requested_path)

    def list_directory(self, path):
        """Disable directory listings."""
        self.send_error(403, "Directory listing is disabled")
        return None

    def do_GET(self):
        """Handle browser GET requests."""

        # Remove query parameters before routing.
        request_path = urlsplit(self.path).path

        # Browsers sometimes request a favicon automatically.
        if request_path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return

        self.path = request_path

        super().do_GET()


def main():
    """Start the CivicTrack development server."""

    server = ThreadingHTTPServer(
        (HOST, PORT),
        CivicTrackHandler,
    )

    print()
    print("===================================")
    print("          CIVICTRACK v0.1")
    print("===================================")
    print()
    print(f"Server: http://{HOST}:{PORT}/")
    print("Press Ctrl+C to stop the server.")
    print()

    try:
        server.serve_forever()

    except KeyboardInterrupt:
        print("\nShutting down CivicTrack...")

    finally:
        server.server_close()
        print("Server stopped.")


if __name__ == "__main__":
    main()

