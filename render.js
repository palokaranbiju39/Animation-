// Seeks every frame at 30fps with Playwright and pipes PNG screenshots, in order, into ffmpeg (H.264 yuv420p).
const {chromium}=require('playwright');const {spawn}=require('child_process');
const FPS=30, DUR=42.0, W=4, OUT=process.argv[2]||'plix-reel.mp4', AUDIO='plix-audio.wav';
(async()=>{
  const total=Math.round(FPS*DUR);
  const ff=spawn('ffmpeg',['-y','-v','error','-f','image2pipe','-framerate',String(FPS),'-c:v','png','-i','-','-i',AUDIO,
    '-map','0:v','-map','1:a','-c:v','libx264','-preset','medium','-crf','17','-pix_fmt','yuv420p','-r',String(FPS),
    '-c:a','aac','-b:a','256k','-movflags','+faststart','-shortest',OUT],{stdio:['pipe','inherit','inherit']});
  const browser=await chromium.launch();
  const pages=[];
  for(let i=0;i<W;i++){const p=await browser.newPage({viewport:{width:1080,height:1920}});await p.goto('file://'+process.cwd()+'/index.html');await p.waitForFunction(()=>window.seek);pages.push(p)}
  const jobs=new Map();let next=0;const t0=Date.now();
  const start=(idx)=>{const p=pages[idx%W];const prev=jobs.get(idx-W)||Promise.resolve();
    const job=prev.then(async()=>{await p.evaluate(t=>window.seek(t),idx/FPS);return p.screenshot({type:'png'})});jobs.set(idx,job);return job};
  for(let i=0;i<Math.min(total,W*2);i++)start(i);next=Math.min(total,W*2);
  for(let i=0;i<total;i++){
    const buf=await jobs.get(i);jobs.delete(i);
    if(!ff.stdin.write(buf))await new Promise(r=>ff.stdin.once('drain',r));
    if(next<total){start(next);next++}
    if(i%60===0)console.log(`frame ${i}/${total}  ${((Date.now()-t0)/1000).toFixed(0)}s`);
  }
  ff.stdin.end();await new Promise(r=>ff.on('close',r));await browser.close();console.log('done',OUT);
})();
