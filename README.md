# Cloud YouTube Shorts Factory

A cloud-only YouTube Shorts autopilot. Nothing needs to be installed on your computer.

## What it does

1. Runs automatically from GitHub Actions.
2. Chooses a topic from the configured topic pool.
3. Uses OpenAI to generate an original Short package.
4. Uses OpenAI text-to-speech to create narration.
5. Builds a vertical 1080x1920 Short with animated visuals, captions, and narration.
6. Runs duration/format QA.
7. Publishes the finished video through the official YouTube Data API.
8. Repeats on the hourly GitHub Actions schedule.

## Cloud architecture

GitHub Actions -> OpenAI -> cloud video renderer -> YouTube

The GitHub Actions runner is temporary. Generated work files disappear after each run, so your computer does not need to stay on.

## Required GitHub secrets

Add these in the repository's **Settings -> Secrets and variables -> Actions**:

- `OPENAI_API_KEY`
- `YOUTUBE_TOKEN_JSON`

Never commit either secret to the repository.

### YouTube authorization

YouTube publishing requires one-time OAuth authorization for the channel. The resulting authorized-user token JSON is stored as the `YOUTUBE_TOKEN_JSON` GitHub secret.

## Configuration

Edit `config/config.json` to change:

- posting interval/schedule
- Short duration
- topic categories
- YouTube privacy status
- OpenAI text model
- OpenAI TTS model and voice

## Manual run

GitHub Actions also exposes **Run workflow**, so you can trigger a Short manually without installing anything.

## Important

GitHub Actions scheduling is best-effort, so an hourly job can start a little later than the exact minute. OpenAI API usage and YouTube API usage are subject to their current quotas/pricing.

## Security

- API keys are read only from environment variables.
- No secrets are stored in source code.
- YouTube uploads use Google's official API and OAuth.
