import json
import os
import random
import re
import subprocess
from datetime import datetime, timezone

from openai import OpenAI

from .render import render_short
from .youtube import upload_video


def _parse_json(text: str):
    text = text.strip()
    text = re.sub(r"^\s*\`\`\`(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*\`\`\`\s*$", "", text)
    return json.loads(text)


def generate_package(client, config):
    topic = random.choice(config["topic_pool"])
    prompt = f"""
Create one original factual YouTube Short about "{topic}".

Return ONLY valid JSON with this schema:
{{
  "title": "short title",
  "description": "short description",
  "hashtags": ["#shorts", "#..."],
  "hook": "opening hook",
  "narration": "90-120 word narration",
  "scenes": [
    {{
      "visual_prompt": "cinematic visual description",
      "on_screen_text": "very short caption"
    }}
  ]
}}

Use exactly 6 scenes. Keep the narration fast, natural, and interesting.
Do not invent facts. If something is genuinely uncertain, describe it as uncertain.
Do not use clickbait that falsely states something is proven.
"""
    response = client.responses.create(
        model=config["model"],
        input=prompt,
    )
    package = _parse_json(response.output_text)

    required = ["title", "description", "narration", "scenes"]
    missing = [key for key in required if not package.get(key)]
    if missing:
        raise RuntimeError(f"Generated package is missing: {', '.join(missing)}")
    if not isinstance(package["scenes"], list) or len(package["scenes"]) < 4:
        raise RuntimeError("Generated package did not contain enough scenes")

    package["topic"] = topic
    return package


def synthesize_speech(client, text, output, config):
    speech = client.audio.speech.create(
        model=config.get("tts_model", "gpt-4o-mini-tts"),
        voice=config.get("tts_voice", "alloy"),
        input=text,
        response_format="mp3",
        instructions="Energetic, natural YouTube Shorts narration. Clear diction. Medium-fast pacing.",
    )
    speech.write_to_file(str(output))


def run_pipeline(config, root):
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Missing OPENAI_API_KEY")
    if not os.getenv("YOUTUBE_TOKEN_JSON"):
        raise RuntimeError("Missing YOUTUBE_TOKEN_JSON")

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    job = root / "work" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    job.mkdir(parents=True, exist_ok=True)

    package = generate_package(client, config)
    (job / "package.json").write_text(
        json.dumps(package, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    audio_path = job / "voice.mp3"
    synthesize_speech(client, package["narration"], audio_path, config)

    video_path = job / "short.mp4"
    render_short(
        package,
        video_path,
        job,
        config,
        external_audio=audio_path,
    )

    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    duration = float(probe.stdout.strip())

    if not 10 <= duration <= 60:
        raise RuntimeError(f"QA failed: duration={duration:.2f}s")

    privacy = os.getenv(
        "YOUTUBE_PRIVACY_STATUS",
        config.get("privacy_status", "public"),
    )

    video_id = upload_video(
        video_path,
        package["title"],
        package["description"] + "\n\n" + " ".join(package.get("hashtags", [])),
        config.get("category_id", "22"),
        privacy,
    )

    result = {
        "status": "published",
        "video_id": video_id,
        "title": package["title"],
        "duration_seconds": duration,
        "topic": package["topic"],
        "job": str(job),
    }
    (job / "result.json").write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )
    return result
