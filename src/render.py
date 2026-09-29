import math
import random
import subprocess
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

W, H, FPS = 1080, 1920, 30
BG = (7, 9, 14)
WHITE = (248, 249, 252)
MUTED = (178, 185, 198)
ACCENT = (85, 210, 255)


def font(size, bold=False):
    path = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    )
    return ImageFont.truetype(path, size)


def wrap(text, limit=27):
    lines = []
    current = ""
    for word in text.split():
        candidate = (current + " " + word).strip()
        if len(candidate) > limit and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def download_image(url, destination):
    if not url:
        return None
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "CloudShortsFactory/1.0"},
            timeout=20,
        )
        response.raise_for_status()
        destination.write_bytes(response.content)
        image = Image.open(destination).convert("RGB")
        if image.width < 500 or image.height < 500:
            return None
        return image
    except Exception:
        return None


def fallback_background(seed):
    rng = np.random.default_rng(seed)
    base = rng.integers(12, 38, 3)
    yy = np.linspace(0, 1, H)[:, None]
    xx = np.linspace(0, 1, W)[None, :]
    glow = (
        np.sin((xx * 3.2 + yy * 1.4) * math.pi)
        + np.cos((yy * 4.0 - xx) * math.pi)
    ) * 18
    array = np.zeros((H, W, 3), dtype=np.uint8)
    for channel in range(3):
        array[:, :, channel] = np.clip(base[channel] + glow, 0, 255)
    return Image.fromarray(array)


def cinematic_crop(image, t, scene_index):
    image = image.convert("RGB")
    target_ratio = W / H
    source_ratio = image.width / image.height

    if source_ratio > target_ratio:
        crop_h = image.height
        crop_w = int(crop_h * target_ratio)
    else:
        crop_w = image.width
        crop_h = int(crop_w / target_ratio)

    zoom = 1.02 + 0.09 * t
    crop_w = max(2, int(crop_w / zoom))
    crop_h = max(2, int(crop_h / zoom))

    max_x = max(0, image.width - crop_w)
    max_y = max(0, image.height - crop_h)

    direction = 1 if scene_index % 2 == 0 else -1
    pan = 0.5 + direction * 0.30 * math.sin(t * math.pi / 2)
    x = int(max_x * min(1, max(0, pan)))
    y = int(max_y * (0.42 + 0.16 * math.sin(t * math.pi)))

    cropped = image.crop((x, y, x + crop_w, y + crop_h))
    return ImageOps.fit(cropped, (W, H), method=Image.Resampling.LANCZOS)


def overlay_gradient(im):
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pixels = np.zeros((H, W, 4), dtype=np.uint8)
    y = np.linspace(0, 1, H)[:, None]
    top = np.clip((0.42 - y) * 2.0, 0, 1)
    bottom = np.clip((y - 0.46) * 1.8, 0, 1)
    alpha = np.clip((top + bottom) * 155, 0, 205)
    pixels[:, :, 3] = alpha.astype(np.uint8)
    Image.fromarray(pixels, "RGBA").putalpha(Image.fromarray(pixels[:, :, 3]))
    overlay = Image.fromarray(pixels, "RGBA")
    return Image.alpha_composite(im.convert("RGBA"), overlay)


def add_vignette(im):
    yy, xx = np.mgrid[0:H, 0:W]
    dx = (xx - W / 2) / (W / 2)
    dy = (yy - H / 2) / (H / 2)
    distance = np.sqrt(dx * dx + dy * dy)
    alpha = np.clip((distance - 0.35) * 120, 0, 105).astype(np.uint8)
    vignette = np.zeros((H, W, 4), dtype=np.uint8)
    vignette[:, :, 3] = alpha
    vignette[:, :, 0:3] = 0
    return Image.alpha_composite(im, Image.fromarray(vignette, "RGBA"))


def add_grain(im, rng, strength=8):
    noise = rng.normal(0, strength, (H, W, 1))
    array = np.asarray(im.convert("RGB"), dtype=np.float32)
    array = np.clip(array + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(array).convert("RGBA")


def draw_caption(draw, text, y=1260):
    lines = wrap(text)[:4]
    box_h = 90 + len(lines) * 76
    box = (55, y, 1025, y + box_h)

    draw.rounded_rectangle(
        box,
        radius=34,
        fill=(5, 7, 12, 218),
        outline=(255, 255, 255, 36),
        width=2,
    )
    draw.rounded_rectangle(
        (82, y + 32, 94, y + box_h - 32),
        radius=6,
        fill=ACCENT,
    )

    cursor_y = y + 30
    for line in lines:
        draw.text(
            (122, cursor_y),
            line,
            font=font(45, True),
            fill=WHITE,
            stroke_width=1,
            stroke_fill=(0, 0, 0, 170),
        )
        cursor_y += 76


def render_short(package, output, work, config, external_audio):
    scenes = package.get("scenes") or [{"on_screen_text": package.get("hook", "")}]
    target_seconds = float(config.get("duration_seconds", 38))
    seconds_per_scene = max(2.8, target_seconds / len(scenes))

    frames = work / "frames"
    frames.mkdir(exist_ok=True)

    source_path = work / "source_visual.jpg"
    source = download_image(package.get("image_url", ""), source_path)

    # Pre-build the soft background once; the sharp foreground gets animated per frame.
    if source:
        soft = ImageOps.fit(source, (W, H), method=Image.Resampling.LANCZOS)
        soft = soft.filter(ImageFilter.GaussianBlur(26))
        soft = ImageEnhance.brightness(soft).enhance(0.35) if False else soft
    else:
        soft = None

    frame_index = 0
    total_frames = max(1, int(target_seconds * FPS))

    for scene_index, scene in enumerate(scenes):
        count = max(1, int(seconds_per_scene * FPS))
        seed = sum(ord(c) for c in scene.get("visual_prompt", "")) + scene_index * 997
        rng = np.random.default_rng(seed + 42)

        for frame in range(count):
            t = frame / max(1, count - 1)

            if source:
                foreground = cinematic_crop(source, t, scene_index)
                if soft:
                    canvas = soft.copy().convert("RGBA")
                    canvas.alpha_composite(foreground.convert("RGBA"))
                else:
                    canvas = foreground.convert("RGBA")
            else:
                canvas = fallback_background(seed + frame).convert("RGBA")

            canvas = overlay_gradient(canvas)
            canvas = add_vignette(canvas)
            canvas = add_grain(canvas, rng)

            draw = ImageDraw.Draw(canvas, "RGBA")

            # Editorial header.
            draw.text(
                (68, 76),
                "DOCUMENTARY  /  FACT FILE",
                font=font(25, True),
                fill=WHITE,
                stroke_width=1,
                stroke_fill=(0, 0, 0, 150),
            )
            draw.text(
                (1012, 76),
                f"{scene_index + 1:02d}",
                font=font(30, True),
                fill=ACCENT,
                anchor="ra",
            )

            # Thin cinematic frame lines.
            draw.line((68, 126, 1012, 126), fill=(255, 255, 255, 65), width=2)
            draw.line((68, 1790, 1012, 1790), fill=(255, 255, 255, 55), width=2)

            draw_caption(draw, scene.get("on_screen_text", ""))

            # Animated progress bar.
            progress = min(
                1.0,
                (scene_index + t) / max(1, len(scenes)),
            )
            draw.rounded_rectangle(
                (68, 1820, 1012, 1828),
                radius=4,
                fill=(255, 255, 255, 50),
            )
            draw.rounded_rectangle(
                (68, 1820, 68 + int(944 * progress), 1828),
                radius=4,
                fill=ACCENT,
            )

            # Small moving light accent adds depth without distracting from the source image.
            lx = int(110 + 860 * (0.5 + 0.5 * math.sin(t * math.pi)))
            draw.ellipse(
                (lx - 3, 150, lx + 3, 156),
                fill=(255, 255, 255, 180),
            )

            # Fade between scenes.
            fade_frames = min(12, count // 5)
            fade = 0
            if frame < fade_frames:
                fade = int(145 * (1 - frame / max(1, fade_frames)))
            elif frame >= count - fade_frames:
                fade = int(120 * ((frame - (count - fade_frames)) / max(1, fade_frames)))

            if fade:
                black = Image.new("RGBA", (W, H), (0, 0, 0, fade))
                canvas = Image.alpha_composite(canvas, black)

            canvas.convert("RGB").save(frames / f"frame_{frame_index:06d}.jpg", quality=92)
            frame_index += 1

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            str(FPS),
            "-i",
            str(frames / "frame_%06d.jpg"),
            "-i",
            str(external_audio),
            "-filter_complex",
            "[1:a]loudnorm=I=-16:LRA=7:TP=-1.5[a]",
            "-map",
            "0:v",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "19",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-shortest",
            "-movflags",
            "+faststart",
            str(output),
        ],
        check=True,
    )
