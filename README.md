# YouTube Shorts Factory

Automated hourly YouTube Shorts generator and publisher.

Pipeline: idea -> script -> OpenAI TTS -> animated 9:16 render -> QA -> YouTube upload -> log.

The GitHub Actions workflow runs at the top of every hour and can also be started manually.

Required GitHub Actions secrets:
- OPENAI_API_KEY
- YOUTUBE_CLIENT_SECRETS_JSON
- YOUTUBE_TOKEN_JSON

Run python scripts/auth_youtube.py locally once to create youtube_token.json, then put that JSON into YOUTUBE_TOKEN_JSON.
Create Google OAuth desktop-app credentials and put the downloaded JSON in client_secrets.json.
Required YouTube scope: https://www.googleapis.com/auth/youtube.upload

Set YOUTUBE_PRIVACY_STATUS=private while testing. The default workflow uses public.

GitHub Actions cron is best-effort and may be delayed; it is configured once per hour, not guaranteed at an exact minute.