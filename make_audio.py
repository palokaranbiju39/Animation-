#!/usr/bin/env python3
"""Generates music + SFX in code, ducks them under plix-voiceover.mp3, masters to ~-10 LUFS."""
import numpy as np, subprocess, wave, json, re, sys
SR=44100; DUR=42.0; N=int(SR*DUR)
rng=np.random.default_rng(7)
t_all=np.arange(N)/SR

def decode(path):
    raw=subprocess.run(['ffmpeg','-v','error','-i',path,'-f','f32le','-ac','1','-ar',str(SR),'-'],capture_output=True,check=True).stdout
    return np.frombuffer(raw,dtype=np.float32).copy()
voice=decode('plix-voiceover.mp3')
voice=voice/ (np.abs(voice).max()+1e-9)*0.9
V=np.zeros(N,dtype=np.float32); V[:min(N,len(voice))]=voice[:N]

def lp(x,fc):
    fc=np.broadcast_to(np.asarray(fc,dtype=np.float64),x.shape)
    a=1-np.exp(-2*np.pi*fc/SR); y=np.empty_like(x); s=0.0
    for i in range(len(x)):
        s+=a[i]*(x[i]-s); y[i]=s
    return y
def place(buf,sig,t0,gain=1.0):
    i=int(t0*SR); 
    if i>=len(buf): return
    j=min(len(buf),i+len(sig)); buf[i:j]+=sig[:j-i]*gain
def env_ad(n,a,d):
    t=np.arange(n)/SR; return np.minimum(t/a,1)*np.exp(-t/d)
def bell(f,dur=1.6,dec=.45,h=(1,2.01,3.02,4.2),hg=(1,.45,.2,.1)):
    n=int(dur*SR);t=np.arange(n)/SR;s=sum(g*np.sin(2*np.pi*f*m*t) for m,g in zip(h,hg))
    return (s*env_ad(n,.004,dec)).astype(np.float32)*0.35
def whoosh(dur=.7,f0=300,f1=3500):
    n=int(dur*SR);x=rng.standard_normal(n).astype(np.float32)
    k=np.linspace(0,1,n); fc=f0*(f1/f0)**np.sin(k*np.pi/2)
    y=lp(x,fc); y=y-lp(y,fc*.35)
    e=np.sin(np.pi*k)**1.6; return (y*e).astype(np.float32)*2.2
def thud(f=90,dur=.35,noise=.4):
    n=int(dur*SR);t=np.arange(n)/SR
    s=np.sin(2*np.pi*(f+60*np.exp(-t*30))*t)*np.exp(-t*14)
    nz=lp(rng.standard_normal(n).astype(np.float32),700)*np.exp(-t*25)*noise*4
    return (s+nz).astype(np.float32)*.8
def chirp(f0,f1,dur):
    n=int(dur*SR);t=np.arange(n)/SR;f=np.linspace(f0,f1,n);ph=2*np.pi*np.cumsum(f)/SR
    return (np.sin(ph)*np.sin(np.pi*t/dur)**2).astype(np.float32)*.25

SFX=np.zeros(N,dtype=np.float32)
# wind beds
for a,b,g in[(0,6.6,.9),(23.0,41,.9)]:
    n=int((b-a)*SR);w=lp(rng.standard_normal(n).astype(np.float32),400+250*np.sin(np.arange(n)/SR*.7))*3
    fade=np.minimum(1,np.minimum(np.arange(n)/SR/1.0,(n-np.arange(n))/SR/1.0));place(SFX,w*fade*.22,a,g)
# transitions
for t0,d in[(0.0,.5),(6.25,.7),(15.0,.7),(23.0,.7),(28.0,.8),(36.9,.9),(39.75,.6)]: place(SFX,whoosh(d),t0,.55)
# doorbell
place(SFX,bell(784,1.4,.5,(1,2),(1,.3)),2.35,.9);place(SFX,bell(659,1.6,.6,(1,2),(1,.3)),2.7,.9)
# box handover thump
place(SFX,thud(120,.3,.3),3.9,.5)
# unbox pop + sparkles
n=int(.25*SR);t=np.arange(n)/SR;pop=(np.sin(2*np.pi*(300+2400*t)*t)*np.exp(-t*18)).astype(np.float32);place(SFX,pop,7.25,.8)
place(SFX,(lp(rng.standard_normal(int(.2*SR)).astype(np.float32),5000)*np.exp(-np.arange(int(.2*SR))/SR*30)).astype(np.float32),7.22,.6)
for i,f in enumerate([1047,1319,1568,2093,2637,3136]): place(SFX,bell(f,1.0,.3,(1,2.7),(1,.3)),7.6+i*.13,.45)
for t0 in[10.1,11.9,13.5]: place(SFX,bell(2093,.9,.3,(1,2.7),(1,.3)),t0,.3)
# phone
place(SFX,bell(1319,1.0,.28)*1,16.9,.8);place(SFX,bell(1760,1.2,.3),17.02,.8)
place(SFX,bell(1319,1.0,.28),18.8,.8);place(SFX,bell(1760,1.2,.3),18.92,.8);place(SFX,bell(2349,1.3,.35),19.06,.7)
for i,f in enumerate([1047,1319,1568]): place(SFX,bell(f,1.0,.3),21.8+i*.1,.55)
# digging, planting, patting
for t0 in[24.1,24.38,24.62]: place(SFX,thud(80,.3,.8),t0,.9)
place(SFX,lp(rng.standard_normal(int(.7*SR)).astype(np.float32),2500)*np.hanning(int(.7*SR))*.5,23.5,.5)
place(SFX,thud(70,.45,.5),26.0,.9)
for t0 in[26.45,26.7,26.95,27.2]: place(SFX,thud(110,.2,.5),t0,.55)
n=int(1.1*SR);pour=rng.standard_normal(n).astype(np.float32);pour=pour-lp(pour,1500);place(SFX,pour*np.hanning(n)*.25,27.5,.9)
# growth shimmers
for t0 in[28.7,30.2,32.0,34.0,36.0]:
    n=int(1.3*SR);t=np.arange(n)/SR;f=np.linspace(600,2400,n);s=np.sin(2*np.pi*np.cumsum(f)/SR)*np.sin(np.pi*t/1.3)**2;place(SFX,s.astype(np.float32)*.18,t0,1)
# rain
n=int(2.3*SR);rain=rng.standard_normal(n).astype(np.float32);rain=rain-lp(rain,1800);rain=lp(rain,9000)
fade=np.minimum(1,np.minimum(np.arange(n)/SR/.5,(n-np.arange(n))/SR/.6));place(SFX,rain*fade*.35,31.3,1)
# crickets at night
for t0 in np.arange(29.9,31.2,.11): place(SFX,(np.sin(2*np.pi*4200*np.arange(int(.04*SR))/SR)*np.hanning(int(.04*SR))).astype(np.float32)*.08,t0)
# birds
for t0 in np.arange(33.9,40.2,.38):
    r=rng.random()
    if r<.6:
        f=rng.uniform(2200,3600);place(SFX,chirp(f,f*rng.uniform(.8,1.35),rng.uniform(.07,.16)),t0+rng.uniform(0,.2),.55)
# end sting & chime
for i,f in enumerate([523,659,784,1047]): place(SFX,bell(f,2.2,.9),37.4+i*.09,.6)
for f in[523,659,784,1047,1319]: place(SFX,bell(f,2.4,1.0),40.0,.45)

# ---- music: pad + kalimba pluck, C maj7 / Am7 / Fmaj7 / G6, 80 bpm
beat=60/80; bar=4*beat
chords=[[130.81,164.81,196,246.94],[110,164.81,196,261.63],[87.31,130.81,174.61,220],[98,146.83,196,246.94]]
M=np.zeros(N,dtype=np.float32)
for b in range(int(DUR/bar)+1):
    ch=chords[b%4];t0=b*bar;n=int(bar*SR*1.25);t=np.arange(n)/SR
    e=np.minimum(t/.8,1)*np.minimum(1,(bar*1.25-t)/.9)
    pad=sum(np.sin(2*np.pi*f*t)+.5*np.sin(2*np.pi*f*2*1.003*t)+.25*np.sin(2*np.pi*f*.997*t) for f in ch)
    place(M,(pad*e).astype(np.float32)*.035,t0)
    arp=[ch[0]*2,ch[2]*2,ch[3]*2,ch[1]*4,ch[3]*2,ch[2]*4,ch[1]*4,ch[2]*2]
    for k,f in enumerate(arp):
        tt=t0+k*beat/2;nn=int(1.1*SR);x=np.arange(nn)/SR
        s=(np.sin(2*np.pi*f*x)+.3*np.sin(2*np.pi*f*4*x)*np.exp(-x*12))*np.exp(-x*3.2)
        place(M,s.astype(np.float32)*.05*(1.15 if k%4==0 else .85),tt)
fi=np.minimum(1,t_all/1.5);fo=np.minimum(1,(DUR-t_all)/2.2);M*=fi*fo

# ---- ducking
env=np.abs(V);k=int(.12*SR);env=np.convolve(env,np.ones(k)/k,'same');env=lp(env.astype(np.float32),6)
env=np.clip(env/ (np.percentile(env,95)+1e-9),0,1)
duck=1-.72*env
mix=V*1.0+M*duck*1.0+SFX*(1-.35*env)*1.0
mix=np.tanh(mix*1.1)/1.1
pcm=(np.clip(mix,-1,1)*32767).astype(np.int16)
with wave.open('/tmp/plix_premix.wav','wb') as w: w.setnchannels(1);w.setsampwidth(2);w.setframerate(SR);w.writeframes(pcm.tobytes())

# ---- loudnorm two-pass to -10 LUFS
cmd=['ffmpeg','-hide_banner','-i','/tmp/plix_premix.wav','-af','loudnorm=I=-10:TP=-1.0:LRA=7:print_format=json','-f','null','-']
out=subprocess.run(cmd,capture_output=True,text=True).stderr
m=json.loads(re.search(r'\{[^{}]*"input_i"[^{}]*\}',out,re.S).group(0))
gain=-7.6-float(m['input_i'])
af=f"volume={gain:.2f}dB,alimiter=limit=0.89:attack=3:release=60:level=disabled"
subprocess.run(['ffmpeg','-y','-v','error','-i','/tmp/plix_premix.wav','-af',af,'-ar','48000','-ac','2','plix-audio.wav'],check=True)
print('measured',m['input_i'],'-> mastered plix-audio.wav')
