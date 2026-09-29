import json, os, random, subprocess
from datetime import datetime, timezone
from pathlib import Path
from .local_ai import generate_package, synthesize_speech
from .render import render_short
from .youtube import upload_video

def run_local_pipeline(config, root):
    topic=random.choice(config["topic_pool"])
    job=root/"work"/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    job.mkdir(parents=True,exist_ok=True)
    package=generate_package(topic)
    (job/"package.json").write_text(json.dumps(package,indent=2),encoding="utf-8")
    synthesize_speech(package["narration"],job/"voice.wav")
    render_short(package,job/"short.mp4",job,config,external_audio=job/"voice.wav")
    q=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(job/"short.mp4")],capture_output=True,text=True,check=True)
    duration=float(q.stdout.strip())
    if not 10<=duration<=60: raise RuntimeError(f"QA failed: duration={duration:.2f}s")
    privacy=os.getenv("YOUTUBE_PRIVACY_STATUS",config.get("privacy_status","public"))
    vid=upload_video(job/"short.mp4",package["title"],package["description"]+"\n\n"+" ".join(package.get("hashtags",[])),config.get("category_id","22"),privacy)
    result={"status":"published","video_id":vid,"title":package["title"],"duration_seconds":duration,"topic":topic,"job":str(job)}
    (job/"result.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    return result
