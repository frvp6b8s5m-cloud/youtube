import subprocess
from pathlib import Path

import requests
from PIL import Image

W, H = 1080, 1920
FPS = 30


def download_image(url, destination):
    if not url:
        return None
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "CloudShortsFactory/1.0"},
            timeout=12,
        )
        response.raise_for_status()
        destination.write_bytes(response.content)
        image = Image.open(destination).convert("RGB")
        if image.width < 500 or image.height < 500:
            return None
        return image
    except Exception:
        return None


def ffmpeg_escape(text):
    return (
        str(text or "")
        .replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("%", "\\%")
        .replace(",", "\\,")
    )


def write_srt(scenes, seconds, path):
    count = max(1, len(scenes))
    per_scene = seconds / count
    lines = []

    for i, scene in enumerate(scenes):
        start = i * per_scene
        end = (i + 1) * per_scene
        caption = scene.get("on_screen_text", "").strip()
        if not caption:
            continue

        def stamp(value):
            hours = int(value // 3600)
            minutes = int((value % 3600) // 60)
            secs = int(value % 60)
            millis = int(round((value - int(value)) * 1000))
            if millis >= 1000:
                secs += 1
                millis = 0
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

        lines.extend([str(i + 1), f"{stamp(start)} --> {stamp(end)}", caption, ""])

    path.write_text("\n".join(lines), encoding="utf-8")


def render_short(package, output, work, config, external_audio):
    scenes = package.get("scenes") or [{"on_screen_text": package.get("hook", "")}]
    target_seconds = max(10.0, min(60.0, float(config.get("duration_seconds", 38))))

    source_path = work / "source_visual.jpg"
    source = download_image(package.get("image_url", ""), source_path)

    # A single native FFmpeg render replaces thousands of Python/Pillow frame writes.
    # This keeps the cinematic treatment while making GitHub Actions dramatically faster.
    if source:
        visual = source_path
    else:
        visual = work / "fallback.png"
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", "color=c=0x07090e:s=1080x1920",
                "-frames:v", "1",
                str(visual),
            ],
            check=True,
            capture_output=True,
        )

    srt = work / "captions.srt"
    write_srt(scenes, target_seconds, srt)

    per_scene = target_seconds / max(1, len(scenes))
    vf = (
        f"scale=1080:1920:force_original_aspect_ratio=increase,"
        f"crop=1080:1920,"
        f"zoompan=z='min(zoom+0.0008,1.10)':"
        f"x='iw/2-(iw/zoom/2)+sin(on/45)*80':"
        f"y='ih/2-(ih/zoom/2)+cos(on/60)*55':"
        f"d=1:s=1080x1920:fps={FPS},"
        "format=yuv420p,"
        "drawbox=x=68:y=126:w=944:h=2:color=white@0.25:t=fill,"
        "drawbox=x=68:y=1790:w=944:h=2:color=white@0.20:t=fill,"
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        "text='DOCUMENTARY / FACT FILE':x=68:y=76:fontsize=25:"
        "fontcolor=white@0.92:borderw=1:bordercolor=black@0.6,"
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        "text='%{eif\\:1+floor(t/"
        + str(per_scene)
        + ")\\:d}':x=980:y=76:fontsize=30:"
        "fontcolor=0x55d2ffff:borderw=1:bordercolor=black@0.5,"
        "eq=contrast=1.05:saturation=1.08,"
        "vignette=PI/4,"
        "noise=alls=5:allf=t+u,"
        "subtitles='"
        + ffmpeg_escape(srt)
        + "':force_style='FontName=DejaVu Sans,FontSize=18,"
        "Bold=1,PrimaryColour=&H00F8F9FC,OutlineColour=&H99000000,"
        "BorderStyle=3,Outline=1,Shadow=0,MarginV=250,Alignment=2'"
    )

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loop", "1",
            "-i", str(visual),
            "-i", str(external_audio),
            "-t", f"{target_seconds:.2f}",
            "-vf", vf,
            "-map", "0:v",
            "-map", "1:a",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "21",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "160k",
            "-ar", "48000",
            "-af", "loudnorm=I=-16:LRA=7:TP=-1.5",
            "-shortest",
            "-movflags", "+faststart",
            str(output),
        ],
        check=True,
    )
