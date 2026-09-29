import json
import os
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

from google_auth_oauthlib.flow import Flow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_FILE = Path("client_secret.json")
OUTPUT_FILE = Path("youtube_token.json")
PORT = int(os.environ.get("OAUTH_PORT", "8000"))
REDIRECT_URI = os.environ.get("OAUTH_REDIRECT_URI", "").strip()

if not REDIRECT_URI:
    raise SystemExit("Set OAUTH_REDIRECT_URI to the HTTPS URL of this Codespaces port ending in /oauth2callback.")
if not CLIENT_FILE.exists():
    raise SystemExit("Put your Google OAuth client JSON in the Codespace workspace as client_secret.json.")

client_config = json.loads(CLIENT_FILE.read_text(encoding="utf-8"))
flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=REDIRECT_URI)
state = secrets.token_urlsafe(32)
authorization_url, _ = flow.authorization_url(
    access_type="offline",
    include_granted_scopes="false",
    prompt="consent",
    state=state,
)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != urlparse(REDIRECT_URI).path:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")
            return

        params = parse_qs(parsed.query)
        if params.get("state", [None])[0] != state:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Invalid OAuth state.")
            return

        if "error" in params:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(("Google returned an error: " + params["error"][0]).encode())
            return

        code = params.get("code", [None])[0]
        if not code:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing authorization code.")
            return

        flow.fetch_token(code=code)
        credentials = flow.credentials
        payload = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
        }
        OUTPUT_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            b"<html><body><h1>YouTube authorization complete.</h1>"
            b"<p>You can close this tab. The Codespace created youtube_token.json.</p></body></html>"
        )

        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def log_message(self, format, *args):
        return

server = HTTPServer(("0.0.0.0", PORT), Handler)
print("\n1. Make sure this port is forwarded in GitHub Codespaces.")
print("2. Open this authorization URL in your browser:\n")
print(authorization_url)
print("\n3. Sign into the Google account that owns the YouTube channel and approve access.")
print("4. After success, youtube_token.json will be created in the Codespace.")
print("5. Add its complete contents to GitHub Actions secret YOUTUBE_TOKEN_JSON.")
print("\nWaiting for Google's callback...")
server.serve_forever()
