#!/usr/bin/env python3
"""Music + surf/breeze/whoosh/pop/chime synthesised in code, anchored to the voiceover's line onsets (timing.json),
ducked under voice_edit.wav, mastered to ~-10 LUFS -> audio.wav"""
import numpy as np, subprocess, wave, json, re, sys
SR=44100
tm=json.load(open('timing.json')); L=tm['L']; SE=tm['speechEnd']; DUR=SE+1.5; N=int(SR*DUR)
rng=np.random.default_rng(11); t_all=np.arange(N)/SR
span=lambda i:(L[i+1] if i<5 else SE)-L[i]
AL=lambda i,f:L[i]+f*span(i)
AN=dict(phone=AL(0,.5),turn0=AL(0,.72),flash=AL(1,.45),wave=AL(3,.4)); AN['peak']=AN['wave']+1.4; AN['waveEnd']=AN['wave']+5.8
def decode(path):
    raw=subprocess.run(['ffmpeg','-v','error','-i',path,'-f','f32le','-ac','1','-ar',str(SR),'-'],capture_output=True,check=True).stdout
    return np.frombuffer(raw,dtype=np.float32).copy()
voice=decode(sys.argv[1] if len(sys.argv)>1 else 'voice_edit.wav'); voice=voice/(np.abs(voice).max()+1e-9)*0.9
V=np.zeros(N,np.float32); V[:min(N,len(voice))]=voice[:N]
def lp(x,fc):
    fc=np.broadcast_to(np.asarray(fc,dtype=np.float64),x.shape);a=1-np.exp(-2*np.pi*fc/SR);y=np.empty_like(x);s=0.0
    for i in range(len(x)):
        s+=a[i]*(x[i]-s);y[i]=s
    return y
hp=lambda x,fc:x-lp(x,fc)
def place(buf,sig,t0,gain=1.0):
    i=int(t0*SR)
    if i>=len(buf) or i+len(sig)<0: return
    j=min(len(buf),i+len(sig)); buf[i:j]+=sig[:j-i]*gain
def eio(t):
    t=np.clip(t,0,1); return np.where(t<.5,2*t*t,1-(-2*t+2)**2/2)
def env_ad(n,a,d):
    t=np.arange(n)/SR; return np.minimum(t/a,1)*np.exp(-t/d)
def bell(f,dur=2.0,dec=.8,h=(1,2.0,3.01,4.17),hg=(1,.4,.18,.08)):
    n=int(dur*SR);t=np.arange(n)/SR;s=sum(g*np.sin(2*np.pi*f*m*t) for m,g in zip(h,hg))
    return (s*env_ad(n,.006,dec)).astype(np.float32)*.3
def whoosh(dur=.8,f0=250,f1=2600):
    n=int(dur*SR);x=rng.standard_normal(n).astype(np.float32);k=np.linspace(0,1,n);fc=f0*(f1/f0)**np.sin(k*np.pi/2)
    y=lp(x,fc);y=y-lp(y,fc*.4);return (y*np.sin(np.pi*k)**1.7).astype(np.float32)*2.0
def swell(t):
    p=((t+1.6)/6.4)%1; return np.where(p<.32,eio(p/.32),1-eio((p-.32)/.68))
def surge(t):
    t=np.asarray(t,dtype=float); up=1-(1-np.clip((t-AN['wave'])/1.4,0,1))**3; dn=1-eio((t-AN['peak'])/4.4)
    return np.where((t<AN['wave'])|(t>AN['waveEnd']),0,np.where(t<AN['peak'],up,dn))
late=lambda t:eio((t-AL(4,.85))/(AL(5,.45)-AL(4,.85)))
def endwave(t):
    t0=DUR-3.6; up=1-(1-np.clip((t-t0)/1.9,0,1))**3; dn=1-eio((t-(DUR-1.7))/1.7); return np.where(t<t0,0,np.where(t<DUR-1.7,up,dn))
sw=swell(t_all)+0.35*surge(t_all)*3+0.3*late(t_all)*swell(t_all)+1.1*endwave(t_all)
n1=rng.standard_normal(N).astype(np.float32)
surf=lp(n1,500+2600*np.clip(sw,0,1.6))*(0.25+0.75*np.clip(sw,0,1.4)); surf=(surf-lp(surf,90))*.9
breeze=lp(rng.standard_normal(N).astype(np.float32),260+160*np.sin(t_all*.45))*(0.5+0.5*np.sin(t_all*.3+1))*2.2
SFX=np.zeros(N,np.float32); fade=np.minimum(1,t_all/.6)*np.minimum(1,(DUR-t_all)/2.0)
BED=0.38  # background surf/breeze level (was 1.0) - reduced, not removed
SFX+=(surf*.26+breeze*.16)*fade*BED
# big wave
n=int(1.6*SR);x=rng.standard_normal(n).astype(np.float32);k=np.linspace(0,1,n);place(SFX,lp(x,300+3800*k)*(k**1.6)*1.8,AN['wave']-.2,.5)
n=int(.9*SR);cr=hp(rng.standard_normal(n).astype(np.float32),500)*np.exp(-np.arange(n)/SR*4);place(SFX,cr*1.4,AN['peak']-.1,.5)
n=int(4.2*SR);k=np.linspace(0,1,n);hs=hp(lp(rng.standard_normal(n).astype(np.float32),5200),1200)*np.exp(-k*2.2);place(SFX,hs*.9,AN['peak'],.5)
for t0,d,g in[(AN['turn0']-.1,.9,.35),(AN['flash']-.25,.8,.55),(AL(4,0)-.5,1.0,.3),(AL(5,.1),1.2,.25)]: place(SFX,whoosh(d),t0,g)
n=int(.22*SR);t=np.arange(n)/SR;pop=(np.sin(2*np.pi*(260+1500*t)*t)*np.exp(-t*20)).astype(np.float32);place(SFX,pop,AN['phone']+.05,.5);place(SFX,bell(1568,1.2,.35),AN['phone']+.22,.35)
for i,f in enumerate([880,1319,1760]): place(SFX,bell(f,2.6,1.0),AN['flash']+i*.12,.8)
for t0 in[AL(1,.8),AL(2,.5),AL(3,.15)]: place(SFX,bell(1319,1.6,.6),t0,.28)
def caw(f=520,dur=.28):
    n=int(dur*SR);t=np.arange(n)/SR;ph=2*np.pi*np.cumsum(f*(1-.35*t/dur))/SR
    s=(np.sign(np.sin(ph))*.5+np.sin(ph))*np.sin(np.pi*t/dur)**.8;return lp(s.astype(np.float32),2200)*.22
for t0 in[1.2,1.55,AN['turn0']+.4,AL(4,.25),AL(5,.05)+.5,AL(5,.05)+.85,AL(5,.45)]: place(SFX,caw(480+rng.uniform(-60,60)),t0,.5)
for i,f in enumerate([523,659,784,1047]): place(SFX,bell(f,3.4,1.4),SE+.05+i*.07,.75)
# music
bpm=66;beat=60/bpm;bar=4*beat
chords=[[110,164.81,196,261.63,329.63],[87.31,130.81,174.61,220,261.63],[130.81,164.81,196,246.94,329.63],[98,146.83,196,246.94,293.66]]
M=np.zeros(N,np.float32)
swellM=1+.9*eio((t_all-(AL(4,0)-1))/6)*(1-eio((t_all-(AL(5,0)+2))/3))
for b in range(int(DUR/bar)+2):
    ch=chords[b%4];t0=b*bar;n=int(bar*SR*1.3);t=np.arange(n)/SR
    e=np.minimum(t/1.2,1)*np.minimum(1,(bar*1.3-t)/1.0)
    pad=sum(np.sin(2*np.pi*f*t)+.4*np.sin(2*np.pi*f*2.004*t)+.3*np.sin(2*np.pi*f*.996*t) for f in ch)
    place(M,(pad*e).astype(np.float32)*.026,t0)
    arp=[ch[0]*2,ch[2]*2,ch[3]*2,ch[4]*2,ch[3]*2,ch[2]*2,ch[1]*4,ch[2]*2]
    for k,f in enumerate(arp):
        nn=int(1.6*SR);x=np.arange(nn)/SR
        s=(np.sin(2*np.pi*f*x)+.35*np.sin(2*np.pi*f*2*x)*np.exp(-x*5)+.12*np.sin(2*np.pi*f*3*x)*np.exp(-x*9))*np.exp(-x*2.4)*np.minimum(x/.004,1)
        place(M,s.astype(np.float32)*.045*(1.15 if k%4==0 else .8),t0+k*beat/2)
M*=swellM*np.minimum(1,t_all/2.0)*np.minimum(1,(DUR-t_all)/2.5)
M*=0.55  # music bed level (was 1.0)
env=np.abs(V);k=int(.12*SR);env=np.convolve(env,np.ones(k)/k,'same');env=lp(env.astype(np.float32),6)
env=np.clip(env/(np.percentile(env,95)+1e-9),0,1)
mix=V*1.0+M*(1-.72*env)+SFX*(1-.45*env); mix=np.tanh(mix*1.1)/1.1
pcm=(np.clip(mix,-1,1)*32767).astype(np.int16)
with wave.open('/tmp/ath_premix.wav','wb') as w: w.setnchannels(1);w.setsampwidth(2);w.setframerate(SR);w.writeframes(pcm.tobytes())
out=subprocess.run(['ffmpeg','-hide_banner','-i','/tmp/ath_premix.wav','-af','loudnorm=I=-10:TP=-1.0:LRA=7:print_format=json','-f','null','-'],capture_output=True,text=True).stderr
m=json.loads(re.search(r'\{[^{}]*"input_i"[^{}]*\}',out,re.S).group(0)); gain=-6.3-float(m['input_i'])
subprocess.run(['ffmpeg','-y','-v','error','-i','/tmp/ath_premix.wav','-af',f"volume={gain:.2f}dB,alimiter=limit=0.86:attack=3:release=60:level=disabled",'-ar','48000','-ac','2','audio.wav'],check=True)
print('DUR',round(DUR,2),'premix LUFS',m['input_i'],'gain',round(gain,2))
