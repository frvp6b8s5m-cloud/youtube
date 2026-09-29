import json, threading
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
ROOT=Path(__file__).resolve().parent
app=FastAPI(title="Local Shorts Factory")
state={"running":False,"last":None,"error":None}
def worker():
    from src.local_pipeline import run_local_pipeline
    state["running"]=True
    try:
        cfg=json.loads((ROOT/"config"/"config.json").read_text())
        state["last"]=run_local_pipeline(cfg,ROOT); state["error"]=None
    except Exception as e:
        state["error"]=str(e)
    finally: state["running"]=False
@app.get("/",response_class=HTMLResponse)
def home():
    return """<!doctype html><html><head><meta name=viewport content='width=device-width,initial-scale=1'><title>Shorts Factory</title><style>
body{margin:0;background:#08090d;color:#f5f5f5;font-family:system-ui;padding:40px}main{max-width:900px;margin:auto}
.card{background:#11131a;border:1px solid #282c36;border-radius:20px;padding:24px;margin:16px 0}
button{background:#fff;color:#000;border:0;border-radius:12px;padding:12px 18px;font-weight:700;cursor:pointer}
pre{white-space:pre-wrap;color:#b8c0d0}</style></head><body><main>
<h1>⚡ Local Shorts Factory</h1><div class=card><h2>Autopilot</h2><p>Generate → render → QA → publish</p><button onclick='run()'>Generate now</button><span id=s></span></div>
<div class=card><h2>Latest job</h2><pre id=o>Loading…</pre></div>
<script>async function load(){let r=await fetch('/status');let x=await r.json();document.querySelector('#s').textContent=x.running?' RUNNING':' IDLE';document.querySelector('#o').textContent=JSON.stringify(x,null,2)}async function run(){await fetch('/generate',{method:'POST'});load()}setInterval(load,3000);load()</script>
</main></body></html>"""
@app.get("/status")
def status(): return JSONResponse(state)
@app.post("/generate")
def generate():
    if state["running"]: return {"ok":False,"message":"A job is already running"}
    threading.Thread(target=worker,daemon=True).start()
    return {"ok":True}
