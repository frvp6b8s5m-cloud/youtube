import json, os, subprocess
from pathlib import Path
from urllib.request import Request, urlopen

OLLAMA_URL=os.getenv("OLLAMA_URL","http://127.0.0.1:11434")
OLLAMA_MODEL=os.getenv("OLLAMA_MODEL","llama3.2:3b")

def _ollama(prompt):
    body=json.dumps({"model":OLLAMA_MODEL,"prompt":prompt,"stream":False,"format":"json"}).encode()
    req=Request(f"{OLLAMA_URL}/api/generate",data=body,headers={"Content-Type":"application/json"})
    with urlopen(req,timeout=180) as r:
        return json.loads(r.read())["response"]

def generate_package(topic):
    prompt=f"""Create a factual, original YouTube Short package about: {topic}.
Return ONLY valid JSON. No markdown.
Schema:
{{"title":"...","description":"...","hashtags":["#..."],"hook":"...","narration":"90-120 words","scenes":[{{"visual_prompt":"cinematic image prompt","on_screen_text":"short caption"}}]}}
Use 6 scenes. Make the hook strong but not misleading. Do not invent facts; if a claim is uncertain, phrase it as documented uncertainty."""
    return json.loads(_ollama(prompt))

def synthesize_speech(text, output):
    model=os.getenv("PIPER_MODEL")
    piper=os.getenv("PIPER_BIN","piper")
    if not model:
        raise RuntimeError("PIPER_MODEL is not configured. Install a Piper voice model and set PIPER_MODEL.")
    subprocess.run([piper,"--model",model,"--output_file",str(output)],input=text,text=True,check=True)
