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
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "CloudShortsFactory/1.0"


def clean(text):
    return re.sub(r"\s+", " ", (text or "").strip())


def wiki_search(topic, limit=12):
    params = {
        "action": "query",
        "list": "search",
        "srsearch": topic,
        "srlimit": limit,
        "format": "json",
    }
    response = requests.get(
        WIKI_API,
        params=params,
        headers={"User-Agent": USER_AGENT},
        timeout=20,
    )
    response.raise_for_status()
    return [item["title"] for item in response.json().get("query", {}).get("search", [])]


def wiki_article(title, max_chars):
    params = {
        "action": "query",
        "prop": "extracts|info",
        "exintro": 1,
        "exsentences": 10,
        "explaintext": 1,
        "inprop": "url",
        "titles": title,
        "format": "json",
        "redirects": 1,
    }
    response = requests.get(
        WIKI_API,
        params=params,
        headers={"User-Agent": USER_AGENT},
        timeout=20,
    )
    response.raise_for_status()
    pages = response.json().get("query", {}).get("pages", {})
    if not pages:
        return None

    page = next(iter(pages.values()))
    if "missing" in page:
        return None

    extract = clean(page.get("extract", ""))
    return {
        "title": page.get("title", title),
        "extract": extract[:max_chars],
        "url": page.get("fullurl", ""),
    }


def commons_visual(title, topic):
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": f"{title} {topic}",
        "gsrnamespace": 6,
        "gsrlimit": 8,
        "prop": "imageinfo",
        "iiprop": "url|mime|extmetadata",
        "iiurlwidth": 1400,
        "format": "json",
    }
    response = requests.get(
        COMMONS_API,
        params=params,
        headers={"User-Agent": USER_AGENT},
        timeout=20,
    )
    response.raise_for_status()

    pages = response.json().get("query", {}).get("pages", {})
    candidates = list(pages.values())
    random.shuffle(candidates)

    for page in candidates:
        info = (page.get("imageinfo") or [{}])[0]
        mime = info.get("mime", "")
        url = info.get("thumburl") or info.get("url")
        if not url or not mime.startswith("image/"):
            continue

        metadata = info.get("extmetadata", {})
        license_name = clean(
            metadata.get("LicenseShortName", {}).get("value", "")
        )
        artist = clean(metadata.get("Artist", {}).get("value", ""))

        return {
            "image_url": url,
            "image_page": f"https://commons.wikimedia.org/wiki/{page.get('title', '').replace(' ', '_')}",
            "image_title": page.get("title", ""),
            "image_license": license_name,
            "image_artist": artist,
        }

    return {}


def sentences(text):
    text = clean(text)
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if len(p.strip()) > 35]


def research(topic, config):
    titles = wiki_search(topic)
    random.shuffle(titles)
    max_chars = min(
        int(config.get("wikipedia", {}).get("max_summary_chars", 1200)),
        1200,
    )

    candidates = []
    for title in titles:
        article = wiki_article(title, max_chars)
        if not article:
            continue

        facts = sentences(article["extract"])
        if len(facts) >= 5:
            article["topic"] = topic
            article["sentence_count"] = len(facts)
            article.update(commons_visual(article["title"], topic))
            return article

        candidates.append((len(facts), article))

    if candidates:
        candidates.sort(key=lambda item: item[0], reverse=True)
        best_count, best = candidates[0]
        raise RuntimeError(
            f"No source contained enough factual sentences for a short; "
            f"best source had {best_count}, need at least 5."
        )

    raise RuntimeError("No sufficiently detailed factual source was found.")


def caption(text):
    words = text.split()
    return text if len(words) <= 11 else " ".join(words[:11]) + "…"


def make_package(article):
    facts = sentences(article["extract"])
    if len(facts) < 5:
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
        scenes.append(
            {
                "visual_prompt": (
                    f"{styles[i]} about {title}; "
                    f"visually represent this documented fact: {fact}"
                ),
                "on_screen_text": caption(fact),
            }
        )

    visual_credit = article.get("image_page", "")
    visual_license = article.get("image_license", "")
    visual_artist = article.get("image_artist", "")
    credit = (
        f"Visual: {visual_credit} "
        f"({visual_license or 'Wikimedia Commons'}"
        f"{', ' + visual_artist if visual_artist else ''})"
    )

    return {
        "title": f"The Strange Story of {title}"[:95],
        "description": (
            f"Factual short about {title}. Source: {article['url']}\n"
            f"{credit}"
        ),
        "hashtags": ["#shorts", "#facts", "#history", "#science"],
        "hook": hook,
        "narration": narration,
        "scenes": scenes,
        "topic": article["topic"],
        "source": article["url"],
        "source_title": title,
        "image_url": article.get("image_url", ""),
        "image_page": visual_credit,
        "image_license": visual_license,
        "image_artist": visual_artist,
    }


def synthesize_speech(text, output):
    subprocess.run(
        [
            "espeak-ng",
            "-v",
            "en-us",
            "-s",
            "158",
            "-p",
            "48",
            "-a",
            "170",
            "-w",
            str(output),
            text,
        ],
        check=True,
    )


def duration(path):
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
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

    (job / "research.json").write_text(
        json.dumps(article, indent=2), encoding="utf-8"
    )
    (job / "package.json").write_text(
        json.dumps(package, indent=2), encoding="utf-8"
    )

    audio = job / "voice.wav"
    synthesize_speech(package["narration"], audio)

    video = job / "short.mp4"
    render_short(package, video, job, config, external_audio=audio)

    seconds = duration(video)
    if not 10 <= seconds <= 60:
        raise RuntimeError(f"QA failed: duration={seconds:.2f}s")

    privacy = os.getenv(
        "YOUTUBE_PRIVACY_STATUS",
        config.get("privacy_status", "private"),
    )
    video_id = upload_video(
        video,
        package["title"],
        package["description"] + "\n\n" + " ".join(package["hashtags"]),
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
    (job / "result.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    return result
