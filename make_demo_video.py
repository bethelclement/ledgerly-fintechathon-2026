"""Render the captured, genuine CLI output into a captioned MP4. Requires Pillow + ffmpeg.
The video is an edited execution walkthrough, not a browser/screen recording.
Run python run_demo.py before this file to refresh actual evidence.
"""
import json, subprocess, textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'demo'; OUT.mkdir(exist_ok=True)
FRAMES=OUT/'frames';FRAMES.mkdir(exist_ok=True)
steps=json.loads((ROOT/'evidence/demo_steps.json').read_text())
SANS='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
MONO='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
font=lambda p,s:ImageFont.truetype(p,s)
fbrand,fontitle,flabel,fmono,fcap=font(BOLD,46),font(BOLD,41),font(BOLD,17),font(MONO,26),font(SANS,30)
W,H=1920,1080
concat=[];srt=[];transcript=['# Ledgerly: actual offline execution walkthrough','', 'Format: captioned MP4, no voiceover. Output captured from `python run_demo.py`; terminal layout is reformatted for readability. Not a browser recording.','']
def clock(t):
 h=t//3600;m=t//60%60;s=t%60;return f'{h:02}:{m:02}:{s:02},000'
for i,step in enumerate(steps):
 lines=step['output'].splitlines()
 # Progressively reveal actual captured output; never invent results.
 for n in range(1,len(lines)+1):
  im=Image.new('RGB',(W,H),'#eef3ef');d=ImageDraw.Draw(im)
  d.rectangle((0,0,W,124),fill='#102d37')
  d.text((80,33),'ledgerly.',font=fbrand,fill='#e1f6b5')
  d.text((375,48),'SME Finance Copilot',font=font(SANS,26),fill='#dce8e5')
  d.rounded_rectangle((1300,35,1840,88),radius=25,fill='#284650')
  d.text((1328,51),'SYNTHETIC DATA  /  NO REAL MONEY',font=flabel,fill='#e1f6b5')
  d.text((82,160),step['title'],font=fontitle,fill='#163d43')
  d.text((84,222),'CAPTURED PYTHON EXECUTION  ·  REFORMATTED FOR READABILITY',font=flabel,fill='#607c79')
  for j in range(8):d.rounded_rectangle((82+j*219,263,82+j*219+198,270),radius=3,fill='#087f70' if j<=i else '#d1dfd7')
  d.rounded_rectangle((80,300,1840,830),radius=18,fill='#102d37')
  d.rectangle((81,355,1839,356),fill='#31505a')
  for x,c in [(111,'#ed916c'),(139,'#e7cf88'),(167,'#a4cd94')]:d.ellipse((x,322,x+11,333),fill=c)
  d.text((206,315),'ledgerly / offline MVP',font=font(MONO,20),fill='#9db6b7')
  cmd=step['command'];d.text((112,382),'> '+cmd,font=font(MONO,24),fill='#dff2b0')
  for k,line in enumerate(lines[:n]):
   color='#e2eeeb'
   if any(x in line for x in ['SKIPPED','unchanged','Pending tool','True','64 passing','False']):color='#dbefae'
   d.text((112,432+k*34),line,font=fmono,fill=color)
  d.text((84,869),'WHAT THIS PROVES',font=flabel,fill='#087f70')
  for k,line in enumerate(textwrap.wrap(step['caption'],104)):
   d.text((82,908+k*43),line,font=fcap,fill='#173c43')
  d.text((82,1035),'FinTechathon 2026  ·  Topic E  ·  Local prototype, not production underwriting',font=font(SANS,17),fill='#607c79')
  d.text((1735,1030),f'{i+1:02} / 08',font=font(BOLD,20),fill='#087f70')
  path=FRAMES/f'{i:02}_{n:02}.png';im.save(path)
  duration=.35 if n<len(lines) else 20-.35*(len(lines)-1)
  concat.extend([f"file '{path}'",f'duration {duration:.3f}'])
 concat.extend([])
 srt.append(f'{i+1}\n{clock(i*20)} --> {clock((i+1)*20)}\n{step["caption"]}\n')
 transcript.extend([f'## {step["title"]}',step['caption'],'','```text',step['output'],'```',''])
concat.append(f"file '{path}'")
(OUT/'frames.txt').write_text('\n'.join(concat)+'\n')
(OUT/'Ledgerly_Demo_Captions.srt').write_text('\n'.join(srt))
(OUT/'Ledgerly_Demo_Transcript.md').write_text('\n'.join(transcript))
subprocess.run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(OUT/'frames.txt'),'-vf','tpad=stop_mode=clone:stop_duration=20','-r','24','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart','-t','160',str(OUT/'Ledgerly_Demo_2m40s.mp4')],check=True)
video = OUT/'Ledgerly_Demo_2m40s.mp4'
duration = float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(video)]))
if duration < 159.9:
    padded = OUT/'padded.mp4'
    subprocess.run(['ffmpeg','-y','-i',str(video),'-vf',f'tpad=stop_mode=clone:stop_duration={160-duration}','-r','24','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart','-t','160',str(padded)],check=True)
    padded.replace(video)
print(video)
