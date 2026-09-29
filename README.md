# Local Shorts Factory

A local-first YouTube Shorts autopilot.

## What it does
1. Chooses a topic.
2. Uses a local Ollama model to write the Short.
3. Uses a local Piper voice to narrate it.
4. Renders a vertical 1080x1920 video with captions and animation.
5. Runs a duration QA check.
6. Publishes through the official YouTube API.
7. Repeats automatically every hour.
8. Provides a local web dashboard at http://127.0.0.1:8000.

## One-time setup
- Install Python 3.12+
- Install FFmpeg
- Install Ollama and pull a local model such as llama3.2:3b
- Install Piper and download a Piper .onnx voice model.
- Complete YouTube OAuth once and set YOUTUBE_TOKEN_JSON to the token JSON.
- Set PIPER_MODEL to the absolute path of the Piper .onnx model.

## Run
Set the environment variables in your shell, then run: python run_factory.py

Leave that process running. It hosts the dashboard and runs the hourly publisher.

## Important
The computer must remain powered on and the process must remain running for hourly jobs. YouTube authorization is the only external service required for publishing. Generation itself is local.
