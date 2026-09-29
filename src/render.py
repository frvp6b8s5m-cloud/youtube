import math,os,subprocess
import numpy as np
from PIL import Image,ImageDraw,ImageFont
W,H,FPS=1080,1920,30
def font(size,bold=False):
    p='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    return ImageFont.truetype(p,size)
def wrap(s,n=28):
    lines=[]; cur=''
    for w in s.split():
        t=(cur+' '+w).strip()
        if len(t)>n and cur: lines.append(cur); cur=w
        else: cur=t
    if cur: lines.append(cur)
    return lines
def render_short(package,out,work,config,external_audio=None):
    audio=external_audio or work/'voice.mp3'
    scenes=package.get('scenes',[]) or [{'on_screen_text':package.get('hook','')}]
    seconds=max(2,float(config.get('duration_seconds',38))/len(scenes))
    frames=work/'frames'; frames.mkdir(exist_ok=True)
    idx=0
    for i,s in enumerate(scenes):
        n=int(seconds*FPS); seed=sum(map(ord,s.get('visual_prompt','')))+i*997
        rng=np.random.default_rng(seed); base=rng.integers(15,70,3)
        for f in range(n):
            t=f/max(1,n-1); yy=np.linspace(0,1,H)[:,None]; xx=np.linspace(0,1,W)[None,:]
            glow=(np.sin((xx*4+t*2)*math.pi)+np.cos((yy*3-t)*math.pi))*18
            a=np.zeros((H,W,3),dtype=np.uint8)
            for ch in range(3): a[:,:,ch]=np.clip(base[ch]+glow+xx*35+yy*25,0,255)
            im=Image.fromarray(a); d=ImageDraw.Draw(im)
            d.rounded_rectangle((70,120,1010,330),radius=36,fill=(8,8,12))
            d.text((105,165),f'{i+1}/{len(scenes)}',font=font(68,True),fill='white')
            y=610
            for line in wrap(s.get('on_screen_text',''))[:5]:
                b=d.textbbox((0,0),line,font=font(46,True)); x=(W-(b[2]-b[0]))//2
                d.text((x+3,y+3),line,font=font(46,True),fill='black'); d.text((x,y),line,font=font(46,True),fill='white'); y+=70
            cx=int(W*(.5+.25*math.sin(t*math.pi*2))); cy=int(H*(.5+.15*math.cos(t*math.pi*2)))
            r0=90+int(30*math.sin(t*math.pi)); d.ellipse((cx-r0,cy-r0,cx+r0,cy+r0),outline='white',width=5)
            im.save(frames/f'frame_{idx:06d}.png'); idx+=1
    subprocess.run(['ffmpeg','-y','-framerate',str(FPS),'-i',str(frames/'frame_%06d.png'),'-i',str(audio),'-c:v','libx264','-preset','veryfast','-crf','23','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-shortest','-movflags','+faststart',str(out)],check=True)
