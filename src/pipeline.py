import json
import os
import random
import re
import subprocess
from datetime import datetime, timezone

import requests

from .render import render_short
from .youtube import upload_video

WIKI_API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "CloudShortsFactory/1.0"


def clean(text):
    return re.sub(r"\\s+", " ", (text or "").strip())


def wiki_search(topic, limit=8):
    params = {"action": "query", "list": "search", "srsearch": topic, "srlimit": limit, "format": "json"}
    response = requests.get(WIKI_API, params=params, headers={"User-Agent": USER_AGENT}, timeout=20)
    response.raise_for_status()
    return [item["title"] for item in response.json().get("query", {}).get("search", [])]


def wiki_article(title, max_chars):
    params = {
        "action": "query", "prop": "extracts|info", "exintro": 1,
        "explaintext": 1, "inprop": "url", "titles": title,
        "format": "json", "redirects": 1,
    }
    response = requests.get(WIKI_API, params=params, headers={"User-Agent": USER_AGENT}, timeout=20)
    response.raise_for_status()
    pages = response.json().get("query", {}).get("pages", {})
    page = next(iter(pages.values()))
    return {
        "title": page.get("title", title),
        "extract": clean(page.get("extract", ""))[:max_chars],
        "url": page.get("fullurl", ""),
    }


def research(topic, config):
    titles = wiki_search(topic)
    random.shuffle(titles)
    max_chars = int(config.get("wikipedia", {}).get("max_summary_chars", 2400))
    for title in titles[:6]:
        article = wiki_article(title, max_chars)
        if len(article["extract"]) >= 400:
            article["topic"] = topic
            return article
    raise RuntimeError("No sufficiently detailed factual source was found.")


def sentences(text):
    return [p.strip() for p in re.split(r"(?<=[.!?])\\s+", text) if len(p.strip()) > 35]


def caption(text):
    words = text.split()
    return text if len(words) <= 11 else " ".join(words[:11]) + "…"


def make_package(article):
    facts = sentences(article["extract"])
    if len(facts) < 4:
        raise RuntimeError("Source did not contain enough factual sentences.")

    title = article["title"].strip()
    hook = f"Most people have never heard the strange story of {title}."
    selected = facts[:6]
    narration = " ".join([hook] + selected[:5])[:1100]

    styles = [
        "dramatic documentary opening",
        "cinematic close-up",
        "wide historical establishing shot",
        "technical documentary illustration",
        "archival montage",
        "dramatic final reveal",
    ]
    scenes = []
    for i, fact in enumerate(selected):
        scenes.append({
            "visual_prompt": f"{styles[i]} about {title}; visually represent this documented fact: {fact}",
            "on_screen_text": caption(fact),
        })

    return {
        "title": f"The Strange Story of {title}"[:95],
        "description": f"Factual short about {title}. Source: {article['url']}",
        "hashtags": ["#shorts", "#facts", "#history", "#science"],
        "hook": hook,
        "narration": narration,
        "scenes": scenes,
        "topic": article["topic"],
        "source": article["url"],
        "source_title": title,
    }


def synthesize_speech(text, output):
    subprocess.run([
        "espeak-ng", "-v", "en-us", "-s", "165", "-p", "48",
        "-a", "170", "-w", str(output), text
    ], check=True)


def duration(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def run_pipeline(config, root):
    if not os.getenv("YOUTUBE_TOKEN_JSON"):
        raise RuntimeError("Missing YOUTUBE_TOKEN_JSON secret")

    job = root / "work" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    job.mkdir(parents=True, exist_ok=True)

    topic = random.choice(config["topic_pool"])
    article = research(topic, config)
    package = make_package(article)

    (job / "research.json").write_text(json.dumps(article, indent=2), encoding="utf-8")
    (job / "package.json").write_text(json.dumps(package, indent=2), encoding="utf-8")

    audio = job / "voice.wav"
    synthesize_speech(package["narration"], audio)

    video = job / "short.mp4"
    render_short(package, video, job, config, external_audio=audio)

    seconds = duration(video)
    if not 10 <= seconds <= 60:
        raise RuntimeError(f"QA failed: duration={seconds:.2f}s")

    privacy = os.getenv("YOUTUBE_PRIVACY_STATUS", config.get("privacy_status", "private"))
    video_id = upload_video(
        video,
        package["title"],
        package["description"] + "\\n\\n" + " ".join(package["hashtags"]),
        config.get("category_id", "22"),
        privacy,
    )

    result = {
        "status": "uploaded",
        "video_id": video_id,
        "title": package["title"],
        "duration_seconds": seconds,
        "topic": package["topic"],
        "source": package["source"],
        "job": str(job),
    }
    (job / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
