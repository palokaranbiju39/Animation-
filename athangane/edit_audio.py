#!/usr/bin/env python3
"""Trim the long pauses of voiceover.mp3 (keeps speech untouched), write voice_edit.wav + timing.js (line onsets in the edited audio)."""
import re,subprocess,json,sys,numpy as np
SR=44100
src=sys.argv[1] if len(sys.argv)>1 else 'voiceover.mp3'
raw=subprocess.run(['ffmpeg','-v','error','-i',src,'-f','f32le','-ac','1','-ar',str(SR),'-'],capture_output=True,check=True).stdout
x=np.frombuffer(raw,dtype=np.float32).copy(); D=len(x)/SR
out=subprocess.run(['ffmpeg','-hide_banner','-i',src,'-af','silencedetect=noise=-33dB:d=0.18','-f','null','-'],capture_output=True,text=True).stderr
st=[float(v) for v in re.findall(r'silence_start: ([\d.]+)',out)];en=[float(v) for v in re.findall(r'silence_end: ([\d.]+)',out)]
chunks=[];s=0.0
for a,b in zip(st,en):
    chunks.append((s,a));s=b
chunks.append((s,D));gaps=[(chunks[i][1],chunks[i+1][0]) for i in range(len(chunks)-1)]
# line boundaries (gaps where a new narration line starts) - estimated from speech durations vs line lengths
LINE_GAPS=[(6.16,6.65),(12.81,13.38),(16.63,17.24),(25.39,25.92),(32.50,32.97)]
def is_line_gap(g): return any(abs(g[0]-l[0])<.05 for l in LINE_GAPS)
BETWEEN,FINAL,ELL,MID,TINY=0.30,0.50,0.22,0.14,0.08
pad=lambda n:np.zeros(int(n*SR),np.float32)
fade=int(.012*SR)
res=[];L=[0.0];pos=0.05;res.append(pad(.05))
def addseg(seg):
    global pos
    seg=seg.copy();seg[:fade]*=np.linspace(0,1,fade);seg[-fade:]*=np.linspace(1,0,fade);res.append(seg);pos+=len(seg)/SR
for i,(a,b) in enumerate(chunks):
    seg=x[int(max(0,a-.03)*SR):int(min(D,b+.03)*SR)]
    addseg(seg)
    if i<len(gaps):
        g=gaps[i];gd=g[1]-g[0]
        if is_line_gap(g): t=FINAL if abs(g[0]-32.50)<.05 else BETWEEN
        elif gd>.45: t=ELL
        elif gd>.3: t=MID
        else: t=TINY
        t=min(t,gd);res.append(pad(t));pos+=t
        if is_line_gap(g): L.append(round(pos,3))
y=np.concatenate(res+[pad(.15)]);speech_end=round(pos,3)
import wave
with wave.open('voice_edit.wav','wb') as w: w.setnchannels(1);w.setsampwidth(2);w.setframerate(SR);w.writeframes((np.clip(y,-1,1)*32767).astype(np.int16).tobytes())
L[0]=0.05
tm={'L':L,'speechEnd':speech_end,'origDur':round(D,2),'editDur':round(len(y)/SR,2)}
open('timing.js','w').write('window.TIMING='+json.dumps(tm)+';\n');json.dump(tm,open('timing.json','w'))
print(tm)
