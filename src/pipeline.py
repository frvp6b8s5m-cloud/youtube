import json,os,random,re,subprocess
from datetime import datetime,timezone
from openai import OpenAI
from .render import render_short
from .youtube import upload_video

def generate_package(config):
    c=OpenAI(api_key=os.environ['OPENAI_API_KEY'])
    topic=random.choice(config['topic_pool'])
    prompt=f"Create one original factual YouTube Short about {topic}. Return ONLY JSON with title, description, hashtags, hook, narration, scenes. scenes must contain 6-8 objects with visual_prompt and on_screen_text. Narration should be 90-120 words."
    r=c.responses.create(model=config['model'],input=prompt)
    text=r.output_text.strip()
    text=re.sub(r'^```json\\s*','',text); text=re.sub(r'\\s*```$','',text)
    return json.loads(text)

def run_pipeline(config,root):
    job=root/'work'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'); job.mkdir(parents=True,exist_ok=True)
    p=generate_package(config); (job/'package.json').write_text(json.dumps(p,indent=2))
    render_short(p,job/'short.mp4',job,config)
    q=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(job/'short.mp4')],capture_output=True,text=True,check=True)
    duration=float(q.stdout.strip())
    if not 10<=duration<=60: raise RuntimeError('QA failed: duration outside Shorts range')
    vid=upload_video(job/'short.mp4',p['title'],p['description']+'\n\n'+' '.join(p.get('hashtags',[])),config.get('category_id','22'),os.getenv('YOUTUBE_PRIVACY_STATUS',config.get('privacy_status','public')))
    result={'status':'published','video_id':vid,'title':p['title'],'duration_seconds':duration}
    (job/'result.json').write_text(json.dumps(result,indent=2)); return result
