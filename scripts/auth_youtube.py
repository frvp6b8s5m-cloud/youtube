from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
SCOPES=['https://www.googleapis.com/auth/youtube.upload']
root=Path(__file__).resolve().parents[1]
client=root/'client_secrets.json'
if not client.exists(): raise SystemExit('Put Google OAuth desktop client JSON at client_secrets.json first.')
flow=InstalledAppFlow.from_client_secrets_file(str(client),SCOPES)
creds=flow.run_local_server(port=0)
(root/'youtube_token.json').write_text(creds.to_json())
print('Created youtube_token.json')
