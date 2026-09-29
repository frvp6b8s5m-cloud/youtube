import math
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30


def font(size, bold=False):
    path = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    )
    return ImageFont.truetype(path, size)


def wrap(text, limit=28):
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


def render_short(package, output, work, config, external_audio):
    scenes = package.get("scenes") or [{"on_screen_text": package.get("hook", "")}]
    target_seconds = float(config.get("duration_seconds", 38))
    seconds_per_scene = max(2.0, target_seconds / len(scenes))

    frames = work / "frames"
    frames.mkdir(exist_ok=True)

    frame_index = 0

    for scene_index, scene in enumerate(scenes):
        count = int(seconds_per_scene * FPS)
        seed = sum(ord(c) for c in scene.get("visual_prompt", "")) + scene_index * 997
        rng = np.random.default_rng(seed)
        base = rng.integers(15, 70, 3)

        for frame in range(count):
            t = frame / max(1, count - 1)

            yy = np.linspace(0, 1, H)[:, None]
            xx = np.linspace(0, 1, W)[None, :]
            glow = (
                np.sin((xx * 4 + t * 2) * math.pi)
                + np.cos((yy * 3 - t) * math.pi)
            ) * 18

            image = np.zeros((H, W, 3), dtype=np.uint8)
            for channel in range(3):
                image[:, :, channel] = np.clip(
                    base[channel] + glow + xx * 35 + yy * 25,
                    0,
                    255,
                )

            im = Image.fromarray(image)
            draw = ImageDraw.Draw(im)

            draw.rounded_rectangle(
                (70, 120, 1010, 330),
                radius=36,
                fill=(8, 8, 12),
            )
            draw.text(
                (105, 165),
                f"{scene_index + 1}/{len(scenes)}",
                font=font(68, True),
                fill="white",
            )

            caption = scene.get("on_screen_text", "")
            y = 610
            for line in wrap(caption)[:5]:
                bbox = draw.textbbox((0, 0), line, font=font(46, True))
                x = (W - (bbox[2] - bbox[0])) // 2
                draw.text((x + 3, y + 3), line, font=font(46, True), fill="black")
                draw.text((x, y), line, font=font(46, True), fill="white")
                y += 70

            cx = int(W * (0.5 + 0.25 * math.sin(t * math.pi * 2)))
            cy = int(H * (0.5 + 0.15 * math.cos(t * math.pi * 2)))
            radius = 90 + int(30 * math.sin(t * math.pi))
            draw.ellipse(
                (cx - radius, cy - radius, cx + radius, cy + radius),
                outline="white",
                width=5,
            )

            im.save(frames / f"frame_{frame_index:06d}.png")
            frame_index += 1

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            str(FPS),
            "-i",
            str(frames / "frame_%06d.png"),
            "-i",
            str(external_audio),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(output),
        ],
        check=True,
    )
