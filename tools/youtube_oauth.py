import json
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def main():
    client_file = Path("client_secret.json")
    if not client_file.exists():
        raise SystemExit("Put your downloaded Google OAuth client JSON in this folder as client_secret.json, then run this script.")

    flow = InstalledAppFlow.from_client_secrets_file(str(client_file), SCOPES)
    credentials = flow.run_local_server(
        host="localhost",
        port=0,
        access_type="offline",
        prompt="consent",
    )

    output = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }

    Path("youtube_token.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    print("Authorization complete.")
    print("Created youtube_token.json. Add its COMPLETE contents to GitHub Actions secret YOUTUBE_TOKEN_JSON.")
    print("Do NOT commit client_secret.json or youtube_token.json to GitHub.")

if __name__ == "__main__":
    main()
