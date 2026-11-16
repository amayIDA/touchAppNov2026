const $=id=>document.getElementById(id);
$('stage').append($('toast'));
let displayOnly=new URLSearchParams(location.search).has('display');
if(displayOnly)document.body.classList.add('display-only');
let config={},state={status:'disconnected'},frame={points:[],blobs:[],touches:[]},lastFrameAt=0;
let effect=new URLSearchParams(location.search).get('experience')||localStorage.getItem('s3-effect')||'gallery',pointerPreview=false,gallery=null;
let desktopFullscreen=false;
if(window.touchDesktop){window.touchDesktop.isFullscreen().then(value=>{desktopFullscreen=value;updateFullscreen();});window.touchDesktop.onFullscreen(value=>{desktopFullscreen=value;updateFullscreen();});}
let corners=[],calibrationTargets=null,toastTimer,guided=null,guidance={active:false};
const TARGETS=[[.08,.08],[.92,.08],[.92,.92],[.08,.92],[.5,.5]];
const names=['Top left','Top right','Bottom right','Bottom left'];
async function api(route,body={}){const response=await fetch('/api/'+route,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const data=await response.json();if(!response.ok)throw Error(data.error||'Action failed.');return data;}
function toast(message,error=false){$('toast').textContent=message;$('toast').className='toast'+(error?' error':'');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').classList.add('hidden'),6000);}
function action(fn){return async event=>{try{await fn(event);}catch(error){toast(error.message,true);}};}
function transportFields(){
  const t=$('transport').value,serial=t==='serial',tuio=t==='tuio';
  $('address-label').textContent=serial?'COM port':tuio?'Frame Grabber source':'Sensor IP address';
  $('address').disabled=tuio;$('address').value=tuio?'127.0.0.1':t===config.transport?config.address||'':serial?'COM3':'192.168.11.3';
  $('address').placeholder=serial?'COM3':'192.168.11.3';
  $('port-label').textContent=serial?'Baud rate':tuio?'TUIO port':'Port';
  $('port').max=serial?4000000:65535;$('port').value=serial?config.baud||1000000:t===config.transport?config.port:tuio?3333:t==='udp'?8089:20108;
  $('connection-note').textContent=tuio?'Keep Frame Grabber scanning. Enable Multitouch → TUIO (port 3333). No sensor handover needed.':serial?'Stop scanning in Frame Grabber before connecting here. S3 uses 1,000,000 baud.':'Stop scanning in Frame Grabber first. Use your adapter’s configured transport, IP and port.';
}
$('transport').addEventListener('change',transportFields);
function renderState(){
  const live=state.status==='streaming',open=['connecting','streaming','waiting','stale'].includes(state.status);
  $('status').className='status'+(live?' live':['error','stale'].includes(state.status)?' error':'');
  $('status').lastElementChild.textContent=live?'Sensor live':state.status==='waiting'?'Waiting for TUIO':state.status==='connecting'?'Connecting…':state.status==='stale'?'Signal interrupted':state.status==='error'?'Connection error':'Sensor offline';
  $('sensor-message').textContent=state.message||'';
  $('connect').classList.toggle('hidden',open);$('disconnect').classList.toggle('hidden',!open);
  for(const id of ['transport','address','port'])$(id).disabled=open||(id==='address'&&$('transport').value==='tuio');
  $('stage-hint').textContent=pointerPreview?'Drag or touch to explore the visuals.':live?(config.corners?'Touch the surface. Make a little magic.':'Run guided calibration to align your screen.'):'Connect the sensor. Let your hands do the rest.';
  if(effect==='picture')$('stage-hint').textContent=pointerPreview?'Click or drag to reveal a picture.':'Touch to reveal a picture. Lift your hand and touch again for the next one.';
  const tuio=config.transport==='tuio';
  $('scan-hz').previousElementSibling.textContent=tuio?'TOUCH FRAME RATE':'SCAN FREQUENCY';
  $('input-caption').textContent=pointerPreview?'Pointer preview · live touches paused in this view':live?(tuio?'Live S3 touches via Frame Grabber':config.corners?'Live S3 input · calibrated surface':'Live S3 scan · calibration needed'):'Waiting for a sensor connection';
  $('stage-mode').innerHTML=`<i></i>${pointerPreview?'POINTER PREVIEW':live?'LIVE SENSOR INPUT':tuio&&state.status==='waiting'?'TOUCH RECEIVER READY':'AWAITING SENSOR INPUT'}`;
  $('background').disabled=tuio||!live||!!frame.learning;
  $('background').textContent=frame.learning?'Recording…':frame.backgroundReady?'Re-record':'Record';
  $('background-check').textContent=tuio?'○ Frame Grabber detection':frame.backgroundReady?'✓ Background recorded':frame.learning?'◌ Recording background…':'○ Background needed';
  $('background-check').classList.toggle('ready',!!frame.backgroundReady);
  $('corners-check').textContent=config.corners?'✓ Screen calibrated':'○ Calibration needed';$('corners-check').classList.toggle('ready',!!config.corners);
  $('calibration-summary').textContent=config.corners?'Alignment saved. Recalibrate after moving the sensor.':'Align automatically with five guided targets.';
  const calibrationReady=live||(tuio&&state.status==='waiting');
  $('auto-calibrate').disabled=!calibrationReady||(!tuio&&!frame.backgroundReady)||!!guided;
  $('display-calibrate').disabled=$('auto-calibrate').disabled;
  $('scan-hz').textContent=live&&frame.hz?frame.hz:'—';
  $('point-count').textContent=live?(tuio?'TUIO':frame.points.length.toLocaleString()):'—';
  $('point-count').nextElementSibling.textContent=tuio?'touch feed · raw scan unavailable':'per revolution';
}
function setEffect(value,persist=true){
  effect=['ripple','flow','tiles','picture','gallery'].includes(value)?value:'ripple';
  document.querySelectorAll('[data-effect]').forEach(button=>{const active=button.dataset.effect===effect;button.classList.toggle('selected',active);button.setAttribute('aria-pressed',String(active));});
  $('effect-caption').textContent={ripple:'01 — RIPPLE FIELD',flow:'02 — LIGHT TRAILS',tiles:'03 — LED TILES',picture:'04 — PICTURE REVEAL',gallery:'05 — TOUCH STORIES'}[effect];
  $('stage').classList.toggle('gallery-active',effect==='gallery');gallery?.setActive(effect==='gallery');
  $('stage-copy').querySelector('h2').innerHTML=effect==='picture'?'A touch.<br><em>A whole new view.</em>':'Touch the<br><em>extraordinary.</em>';
  if(effect!=='picture')$('picture-layer').classList.add('hidden');
  renderState();
  if(persist)localStorage.setItem('s3-effect',effect);
}
document.querySelectorAll('[data-effect]').forEach(button=>button.onclick=()=>setEffect(button.dataset.effect));
window.addEventListener('storage',event=>{if(event.key==='s3-effect')setEffect(event.newValue,false);});setEffect(effect,false);
$('connection-form').addEventListener('submit',action(async event=>{event.preventDefault();$('connect').disabled=true;try{await api('connect',{transport:$('transport').value,address:$('address').value,port:Number($('port').value),baud:Number($('port').value)});}finally{$('connect').disabled=false;}}));
$('disconnect').onclick=action(()=>api('disconnect'));
$('background').onclick=action(async()=>{await api('background');toast('Keep the surface clear for two seconds.');});
$('threshold').oninput=()=>$('threshold-value').textContent=$('threshold').value+' mm';
$('save-settings').onclick=action(async()=>{await api('settings',{threshold:Number($('threshold').value),minPoints:Number($('min-points').value)});toast('Detection settings saved.');});
$('pointer-preview').onchange=()=>{pointerPreview=$('pointer-preview').checked;pointers.clear();$('preview-label').classList.toggle('hidden',!pointerPreview);renderState();};
async function enterDisplay(){
  displayOnly=true;document.body.classList.add('display-only');history.replaceState(null,'','/?display=1');
  // Request within the button gesture; browsers reject requests made after a fetch.
  const fullscreen=window.touchDesktop?(desktopFullscreen?Promise.resolve():window.touchDesktop.toggleFullscreen().then(value=>desktopFullscreen=value)):$('stage').requestFullscreen?.({navigationUI:'hide'});
  if(fullscreen)await fullscreen.catch(()=>toast('Use the full-screen button, or press F11 in your browser.'));
  if(state.status==='disconnected'&&config.address)await api('connect',{transport:config.transport,address:config.address,port:config.port,baud:config.baud});
  updateFullscreen();
}
function updateFullscreen(){const full=!!document.fullscreenElement||desktopFullscreen;$('start-screen').classList.toggle('hidden',!displayOnly||full);$('fullscreen').setAttribute('aria-label',full?'Exit full screen':'Enter full screen');}
$('open-display').onclick=action(enterDisplay);$('start-screen').onclick=action(enterDisplay);
$('show-controls').onclick=action(async()=>{if(window.touchDesktop&&desktopFullscreen)desktopFullscreen=await window.touchDesktop.toggleFullscreen();else if(document.fullscreenElement)await document.exitFullscreen();displayOnly=false;document.body.classList.remove('display-only');history.replaceState(null,'','/');updateFullscreen();});
$('fullscreen').onclick=action(async()=>{if(window.touchDesktop){desktopFullscreen=await window.touchDesktop.toggleFullscreen();updateFullscreen();}else if(document.fullscreenElement)await document.exitFullscreen();else await enterDisplay();});
document.addEventListener('fullscreenchange',updateFullscreen);
$('display-calibrate').onclick=()=>$('auto-calibrate').click();
window.addEventListener('keydown',event=>{if(/INPUT|SELECT|TEXTAREA/.test(event.target.tagName)||event.ctrlKey||event.altKey||event.metaKey)return;const key=event.key.toLowerCase();if(['1','2','3','4','5'].includes(key))setEffect(['ripple','flow','tiles','picture','gallery'][Number(key)-1]);if(key==='f')$('fullscreen').click();if(key==='c')$('show-controls').click();});
updateFullscreen();

// Local sample artwork and an optional user picture; no uploads leave this PC.
const samplePictures=[{src:'/pictures/desert.svg',title:'DESERT AFTERGLOW'},{src:'/pictures/mountains.svg',title:'ALPINE STILLNESS'},{src:'/pictures/ocean.svg',title:'OCEAN DAYDREAM'}];
for(const picture of samplePictures){const image=new Image();image.src=picture.src;}
let customPicture=localStorage.getItem('s3-picture'),pictureIndex=-1,pictureUntil=0,lastPictureAt=-1000,previousPictureTouches=new Set();
function pictureSettings(){const custom=!!customPicture;$('reset-picture').classList.toggle('hidden',!custom);$('picture-note').textContent=custom?'Your picture is available in Picture reveal and Touch slideshow.':'Three sample artworks included. Touch again to change the picture.';if(gallery){gallery.setPictures(galleryPictures());refreshSlideEditor();}}
function revealPicture(now){
  pictureIndex=(pictureIndex+1)%samplePictures.length;const picture=customPicture?{src:customPicture,title:'YOUR PICTURE'}:samplePictures[pictureIndex];
  $('reveal-picture').src=picture.src;$('reveal-picture').alt=customPicture?'Your touch-revealed picture':picture.title.toLowerCase()+' landscape artwork';$('picture-title').textContent=picture.title;pictureUntil=now+5000;lastPictureAt=now;
}
function renderPicture(touches,now){
  const ids=new Set(touches.map(t=>t.id)),newTouch=touches.some(t=>!previousPictureTouches.has(t.id));
  if(effect==='picture'&&!guidance.active){
    if(newTouch&&now-lastPictureAt>800)revealPicture(now);
    if(touches.length&&pictureUntil>0)pictureUntil=Math.max(pictureUntil,now+4000);
    const showing=now<pictureUntil;$('picture-layer').classList.remove('hidden');$('picture-layer').classList.toggle('showing',showing);$('stage-copy').classList.toggle('picture-showing',showing);
  }else{$('picture-layer').classList.add('hidden');$('stage-copy').classList.remove('picture-showing');pictureUntil=0;}
  previousPictureTouches=ids;
}
$('picture-upload').onchange=action(async event=>{
  const file=event.target.files[0];if(!file)return;if(!['image/jpeg','image/png','image/webp'].includes(file.type))throw Error('Choose a JPG, PNG or WebP picture.');if(file.size>30000000)throw Error('Choose a picture smaller than 30 MB.');
  const url=URL.createObjectURL(file),image=new Image();
  try{image.src=url;await image.decode();const scale=Math.min(1,1920/image.naturalWidth,1920/image.naturalHeight),buffer=document.createElement('canvas');buffer.width=Math.max(1,Math.round(image.naturalWidth*scale));buffer.height=Math.max(1,Math.round(image.naturalHeight*scale));buffer.getContext('2d').drawImage(image,0,0,buffer.width,buffer.height);const data=buffer.toDataURL('image/jpeg',.85);localStorage.setItem('s3-picture',data);customPicture=data;pictureSettings();setEffect('picture');toast('Picture ready. Touch the display to reveal it.');}finally{URL.revokeObjectURL(url);event.target.value='';}
});
$('reset-picture').onclick=()=>{localStorage.removeItem('s3-picture');customPicture=null;pictureSettings();};
window.addEventListener('storage',event=>{if(event.key==='s3-picture'){customPicture=event.newValue;pictureSettings();}});pictureSettings();
function galleryPictures(){const copy=[
  {title:'Desert afterglow',description:'Soft dunes, warm coral light and a quiet violet sky. This illustrated landscape captures the changing colours of the desert at sunset.\n\nA single touch opens a new perspective. Explore the collection, reveal each story, and make the display your own.'},
  {title:'Alpine stillness',description:'Layered mountain peaks rise above a turquoise lake. Cool blue tones and a pale moon create a sense of space, reflection and stillness.\n\nMove between the pictures to explore how an interactive LED surface can bring a visual story to life.'},
  {title:'Ocean daydream',description:'Gentle waves meet a sunlit shore as a small sailboat crosses the horizon. Sea-green water and warm sand give this illustrated scene its calm, open character.\n\nUse these sample stories for your demo, or replace the text with your product, destination or brand information.'}
];return samplePictures.map((p,i)=>({...p,...copy[i]})).concat(customPicture?[{src:customPicture,title:'Your picture',description:'Your own image, ready for an interactive story. Add its title and information in the slide editor on the control screen.'}]:[]);}
gallery=new TouchGallery($('stage'),galleryPictures());gallery.setActive(effect==='gallery');
function refreshSlideEditor(){const previous=$('slide-select').value;$('slide-select').replaceChildren(...gallery.pictures.map((_p,i)=>{const option=document.createElement('option');option.value=i;option.textContent=gallery.data(i).title;return option;}));$('slide-select').value=previous!==''&&Number(previous)<gallery.pictures.length?previous:'0';loadSlideEditor();}
function loadSlideEditor(){const p=gallery.data(Number($('slide-select').value)||0);$('slide-title').value=p.title;$('slide-description').value=p.description;}
$('slide-select').onchange=loadSlideEditor;$('save-slide-text').onclick=()=>{gallery.saveText(Number($('slide-select').value),$('slide-title').value,$('slide-description').value);refreshSlideEditor();toast('Slide information saved.');};refreshSlideEditor();
// Manual calibration remains available for unusual mounting arrangements.
function renderCorners(){
  $('corner-list').replaceChildren(...names.map((name,i)=>{const row=document.createElement('div');row.className='corner-row'+(i===corners.length?' active':'');const label=document.createElement('span');label.textContent=`${i+1}. ${name}`;const value=document.createElement('small');value.textContent=corners[i]?`${Math.round(corners[i][0])}, ${Math.round(corners[i][1])}`:'—';row.append(label,value);return row;}));
  document.querySelectorAll('[data-target]').forEach(el=>el.classList.toggle('current',Number(el.dataset.target)===corners.length));
  $('save-calibration').disabled=corners.length!==4;
  $('calibration-feedback').textContent=corners.length===4?'Four corners captured. Save to apply the alignment.':`Select corner ${corners.length+1}: ${names[corners.length].toLowerCase()}.`;
}
function addCorner(x,y){if(corners.length>=4)return;corners.push([x,y]);renderCorners();}
$('calibrate').onclick=()=>{corners=[];calibrationTargets=null;renderCorners();document.querySelector('.dialog-description').textContent=config.transport==='tuio'?'Hold a hand at each physical screen corner and capture it, or click that corner in the incoming TUIO view. Order: top left → top right → bottom right → bottom left. Guided calibration is recommended.':'Record the empty background first. Then hold a hand at each physical corner and capture it, or click that corner in the scan view. Order: top left → top right → bottom right → bottom left.';document.querySelector('.scan-toolbar>span').textContent=config.transport==='tuio'?'TUIO TOUCH VIEW · NORMALIZED 0–1000':'TOP-DOWN SCAN · MILLIMETRES';$('scan-range').parentElement.classList.toggle('hidden',config.transport==='tuio');$('calibration-dialog').showModal();};
$('close-calibration').onclick=()=>$('calibration-dialog').close();
$('reset-corners').onclick=()=>{corners=[];renderCorners();};
$('capture-corner').onclick=()=>{if(Date.now()-lastFrameAt>1000||!frame.blobs?.length)return toast('No fresh hand detection. Check input and clear the background.',true);if(frame.blobs.length!==1)return toast('Keep only one hand in the scan plane.',true);addCorner(frame.blobs[0].x,frame.blobs[0].y);};
$('save-calibration').onclick=action(async()=>{await api('calibration',{corners,targets:calibrationTargets});$('calibration-dialog').close();toast('Screen alignment saved. Touch the LED surface to try it.');});
const scanCanvas=$('scan'),scanContext=scanCanvas.getContext('2d');
function scanTransform(){const w=scanCanvas.clientWidth,h=scanCanvas.clientHeight,r=Number($('scan-range').value);return {w,h,scale:Math.min(w,h)/(r*2),cx:w/2,cy:h/2};}
scanCanvas.onpointerdown=event=>{const rect=scanCanvas.getBoundingClientRect(),t=scanTransform();let x=(event.clientX-rect.left-t.cx)/t.scale,y=(t.cy-event.clientY+rect.top)/t.scale;if(config.transport==='tuio'){x=(event.clientX-rect.left)/t.w*1000;y=(event.clientY-rect.top)/t.h*1000;}addCorner(x,y);};
function drawScan(){
  if(!$('calibration-dialog').open)return;
  const t=scanTransform(),{w,h}=t;resize(scanCanvas,w,h);const c=scanContext;c.clearRect(0,0,w,h);
  const tuio=config.transport==='tuio',xy=(x,y)=>tuio?[x/1000*w,y/1000*h]:[t.cx+x*t.scale,t.cy-y*t.scale];
  c.strokeStyle='#1a2c33';c.lineWidth=1;
  for(let x=0;x<w;x+=40){c.beginPath();c.moveTo(x,0);c.lineTo(x,h);c.stroke();}for(let y=0;y<h;y+=40){c.beginPath();c.moveTo(0,y);c.lineTo(w,y);c.stroke();}
  if(!tuio){c.fillStyle='#b8f66b';c.beginPath();c.arc(t.cx,t.cy,4,0,Math.PI*2);c.fill();c.font='9px Arial';c.fillText('SENSOR',t.cx+9,t.cy+4);}
  c.fillStyle='#658d89';for(const [x,y] of frame.points||[]){const [px,py]=xy(x,y);c.fillRect(px,py,2,2);}
  for(const blob of frame.blobs||[]){const [x,y]=xy(blob.x,blob.y);c.strokeStyle='#b8f66b';c.beginPath();c.arc(x,y,10,0,Math.PI*2);c.stroke();}
  if(corners.length){c.beginPath();corners.forEach(([x,y],i)=>{const p=xy(x,y);i?c.lineTo(...p):c.moveTo(...p);});if(corners.length===4)c.closePath();c.strokeStyle='#b8f66b';c.fillStyle='#b8f66b0b';c.stroke();c.fill();}
  corners.forEach(([x,y],i)=>{const [px,py]=xy(x,y);c.fillStyle='#b8f66b';c.beginPath();c.arc(px,py,10,0,Math.PI*2);c.fill();c.fillStyle='#111';c.font='bold 11px Arial';c.textAlign='center';c.fillText(String(i+1),px,py+4);c.textAlign='left';});
  $('capture-note').textContent=config.transport==='tuio'?'TUIO coordinates shown on a 0–1000 grid.':frame.blobs?.length===1?'Hand detected. Capture when it is at the corner.':frame.blobs?.length>1?'Multiple objects detected. Leave only one hand.':'Waiting for a foreground hand cluster.';
}
// Guided calibration accepts stable, single-hand measurements and requires a
// release between targets. The fifth target verifies the calculated mapping.
function showGuidance(data){guidance=data;$('calibration-overlay').classList.toggle('hidden',!data.active);if(!data.active)return;const target=TARGETS[data.step]||TARGETS[0];$('calibration-target').style.left=target[0]*100+'%';$('calibration-target').style.top=target[1]*100+'%';$('calibration-ring').style.strokeDashoffset=220*(1-(data.progress||0));$('guided-step').textContent=data.step===4?'05 / 05 · ALIGNMENT CHECK':`0${data.step+1} / 05 · AUTO CALIBRATION`;$('guided-message').textContent=data.message||'Hold your hand on the target.';document.querySelector('.calibration-instructions').style.top=data.step===4?'15%':'36%';}
async function publishGuidance(data){showGuidance(data);await api('guidance',data);}
$('auto-calibrate').onclick=action(async()=>{
  if(state.status!=='streaming'&&!(config.transport==='tuio'&&state.status==='waiting'))throw Error('Connect the sensor first.');
  if(config.transport!=='tuio'&&!frame.backgroundReady)throw Error('Record the empty background first.');
  pointerPreview=false;$('pointer-preview').checked=false;$('preview-label').classList.add('hidden');
  guided={step:0,points:[],samples:[],anchor:null,since:0,release:true,busy:false,lastPublish:0};
  await publishGuidance({active:true,step:0,progress:0,message:'Remove your hand to begin.'});
  renderState();toast('Move the LED display window onto the LED screen, then touch each target.');
});
async function cancelGuided(){guided=null;await publishGuidance({active:false});renderState();}
$('cancel-guided').onclick=action(cancelGuided);
window.addEventListener('keydown',event=>{if(event.key==='Escape'&&guidance.active)cancelGuided().catch(error=>toast(error.message,true));});
async function advanceGuided(){
  const g=guided;if(!g||g.busy)return;
  const now=Date.now(),blobs=frame.blobs||[];
  if(g.release){
    if(!blobs.length){if(!g.clearAt)g.clearAt=now;if(now-g.clearAt>350){g.release=false;g.clearAt=0;await publishGuidance({active:true,step:g.step,progress:0,message:g.step===4?'Touch the centre to verify alignment.':'Hold your hand on the glowing target.'});}}else g.clearAt=0;
    return;
  }
  let progress=0,message='Hold your hand on the glowing target.';
  if(blobs.length===1&&Date.now()-lastFrameAt<1200){const p=blobs[0];if(!g.anchor||Math.hypot(p.x-g.anchor.x,p.y-g.anchor.y)>25){g.anchor=p;g.since=now;g.samples=[];}if(g.sampleFrame!==frame.timestamp){g.samples.push([p.x,p.y]);g.sampleFrame=frame.timestamp;}progress=Math.min(1,(now-g.since)/900);message='Hold still…';}
  else{g.anchor=null;g.since=0;g.samples=[];message=blobs.length>1?'Keep only one hand in the scan plane.':'Touch the glowing target.';}
  if(progress>=1&&g.samples.length>=8){
    g.busy=true;const sample=[0,1].map(i=>g.samples.map(p=>p[i]).sort((a,b)=>a-b)[Math.floor(g.samples.length/2)]);
    try{
      if(g.step<4){g.points.push(sample);g.step++;g.release=true;g.anchor=null;g.samples=[];g.since=0;await publishGuidance({active:true,step:g.step,progress:0,message:'Captured. Remove your hand before the next target.'});}
      else{
        const result=await api('check-calibration',{corners:g.points,targets:TARGETS.slice(0,4),center:sample});
        if(!result.ok){await cancelGuided();toast(`Centre check missed by ${Math.round(result.error*100)}% of the screen. Re-run calibration and touch each target precisely.`,true);return;}
        await api('calibration',{corners:g.points,targets:TARGETS.slice(0,4)});await cancelGuided();toast(`Calibration saved. Centre check error: ${(result.error*100).toFixed(1)}% of the screen.`);
      }
    }catch(error){await cancelGuided();toast(error.message,true);}finally{g.busy=false;}
    return;
  }
  if(now-g.lastPublish>180){g.lastPublish=now;publishGuidance({active:true,step:g.step,progress,message}).catch(()=>{});}
}
setInterval(()=>{if(guided)advanceGuided().catch(error=>toast(error.message,true));},100);
// Real touches and explicit pointer preview share the same rendering path.
const canvas=$('visual'),ctx=canvas.getContext('2d'),pointers=new Map();
let waves=[],particles=[],lastEmitted=new Map(),lastRender=performance.now();
function resize(canvas,w,h){const dpr=Math.min(devicePixelRatio||1,2);if(canvas.width!==Math.round(w*dpr)||canvas.height!==Math.round(h*dpr)){canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);canvas.getContext('2d').setTransform(dpr,0,0,dpr,0,0);}}
function pointerPosition(event){const r=canvas.getBoundingClientRect();return {id:'p'+event.pointerId,u:(event.clientX-r.left)/r.width,v:(event.clientY-r.top)/r.height};}
canvas.onpointerdown=event=>{if((!pointerPreview&&event.pointerType!=='touch')||guidance.active)return;canvas.setPointerCapture(event.pointerId);pointers.set(event.pointerId,pointerPosition(event));};
canvas.onpointermove=event=>{if(pointers.has(event.pointerId))pointers.set(event.pointerId,pointerPosition(event));};
canvas.onpointerup=canvas.onpointercancel=event=>pointers.delete(event.pointerId);
window.addEventListener('blur',()=>pointers.clear());
function glow(x,y,r,color){const gradient=ctx.createRadialGradient(x,y,0,x,y,r);gradient.addColorStop(0,color);gradient.addColorStop(1,'transparent');ctx.fillStyle=gradient;ctx.fillRect(x-r,y-r,r*2,r*2);}
function draw(now){
  const w=canvas.clientWidth,h=canvas.clientHeight;resize(canvas,w,h);const dt=Math.min((now-lastRender)/1000,.05);lastRender=now;
  const fresh=Date.now()-lastFrameAt<(config.transport==='tuio'?2500:600);
  const touches=guidance.active?[]:pointerPreview?[...pointers.values()]:[...pointers.values(),...(fresh&&state.status==='streaming'?frame.touches||[]:[])];
  renderPicture(touches,now);
  gallery.setActive(effect==='gallery'&&!guidance.active);if(!guidance.active){if(effect==='gallery')gallery.tick(now);if(!pointerPreview)gallery.sensorTouches(fresh&&state.status==='streaming'?frame.touches||[]:[],$('stage'),now);}
  $('touch-count').textContent=String(touches.length).padStart(2,'0');$('stage-copy').classList.toggle('active',touches.length>0||guidance.active);
  ctx.fillStyle='#071113';ctx.fillRect(0,0,w,h);
  glow(w*.23,h*.85,w*.55,'#0f3b302e');glow(w*.85,h*.4,w*.4,'#153c4629');
  // An LED-like point field remains quiet until a hand enters the surface.
  const spacing=effect==='tiles'?19:21;
  for(let y=14;y<h;y+=spacing)for(let x=14;x<w;x+=spacing){
    let energy=0;
    for(const t of touches)energy=Math.max(energy,Math.exp(-Math.hypot(x-t.u*w,y-t.v*h)/90));
    const ambient=(Math.sin(x*.006+y*.01+now*.00015)+1)*.012;
    ctx.fillStyle=effect==='tiles'?`rgba(${90+energy*95},${125+energy*110},${125-energy*30},${.10+energy*.85})`:`rgba(142,207,177,${.08+ambient+energy*.7})`;
    if(effect==='tiles'){const size=12+energy*2;ctx.fillRect(x-size/2,y-size/2,size,size);}else{ctx.beginPath();ctx.arc(x,y,.65+energy*1.6,0,Math.PI*2);ctx.fill();}
  }
  // Quiet concentric geometry gives the idle screen depth without simulating touch.
  ctx.strokeStyle='#68a98d0c';ctx.lineWidth=1;
  for(let i=0;i<5;i++){ctx.beginPath();ctx.ellipse(w*.52,h*.78,w*(.17+i*.085),h*(.28+i*.13),-.15,0,Math.PI*2);ctx.stroke();}
  const seen=new Set();
  for(const t of touches){
    const x=t.u*w,y=t.v*h,key=t.id;seen.add(key);
    const last=lastEmitted.get(key)||{at:0,x,y};
    if(now-last.at>(effect==='ripple'?170:35)){
      if(effect==='ripple')waves.push({x,y,age:0});
      if(effect==='flow')for(let j=0;j<7;j++){const a=Math.random()*Math.PI*2,s=20+Math.random()*65;particles.push({x,y,vx:Math.cos(a)*s+(x-last.x)*2,vy:Math.sin(a)*s+(y-last.y)*2,age:0,life:1+Math.random()});}
      lastEmitted.set(key,{at:now,x,y});
    }
    glow(x,y,120,effect==='flow'?'#66d9e830':'#c3f78022');
    ctx.strokeStyle='#ccfcaac0';ctx.lineWidth=1.5;ctx.beginPath();ctx.arc(x,y,14+Math.sin(now*.004)*2,0,Math.PI*2);ctx.stroke();
    ctx.fillStyle='#dcffc9';ctx.beginPath();ctx.arc(x,y,3,0,Math.PI*2);ctx.fill();
    ctx.font='8px Arial';ctx.fillStyle='#a3cfa4';ctx.fillText(`TOUCH ${String(key).replace('p','')}`,x+23,y-3);
  }
  for(const key of lastEmitted.keys())if(!seen.has(key))lastEmitted.delete(key);
  waves=waves.filter(p=>p.age<2.6).slice(-100);
  for(const p of waves){p.age+=dt;const radius=12+p.age*110,alpha=Math.max(0,(1-p.age/2.6)*.6);ctx.strokeStyle=`rgba(159,239,173,${alpha})`;ctx.lineWidth=1;ctx.beginPath();ctx.arc(p.x,p.y,radius,0,Math.PI*2);ctx.stroke();ctx.strokeStyle=`rgba(103,208,210,${alpha*.4})`;ctx.beginPath();ctx.arc(p.x,p.y,radius*1.16,0,Math.PI*2);ctx.stroke();}
  particles=particles.filter(p=>p.age<p.life).slice(-1200);
  if(effect==='flow'){ctx.globalCompositeOperation='lighter';for(const p of particles){p.age+=dt;p.x+=p.vx*dt;p.y+=p.vy*dt;p.vx*=.99;p.vy*=.99;ctx.fillStyle=`rgba(103,228,214,${(1-p.age/p.life)*.8})`;ctx.beginPath();ctx.arc(p.x,p.y,1.8,0,Math.PI*2);ctx.fill();}ctx.globalCompositeOperation='source-over';}else particles=[];
  drawScan();requestAnimationFrame(draw);
}
requestAnimationFrame(draw);
async function init(){
  const response=await fetch('/api/config');const data=await response.json();config=data.config;state=data.state;
  $('transport').value=config.transport;transportFields();$('threshold').value=config.threshold;$('threshold-value').textContent=config.threshold+' mm';$('min-points').value=config.minPoints;renderState();
  const events=new EventSource('/api/events');
  events.addEventListener('state',event=>{state=JSON.parse(event.data);renderState();if(guided&&state.status!=='streaming'&&!(config.transport==='tuio'&&state.status==='waiting'))cancelGuided().catch(()=>{});});
  events.addEventListener('frame',event=>{frame=JSON.parse(event.data);lastFrameAt=Date.now();renderState();if(guided)advanceGuided().catch(error=>toast(error.message,true));});
  events.addEventListener('config',event=>{config=JSON.parse(event.data);$('transport').value=config.transport;transportFields();renderState();});
  events.addEventListener('guidance',event=>{const data=JSON.parse(event.data);if(!data.active&&guided){guided=null;renderState();}showGuidance(data);});
  events.onerror=()=>{state={status:'error',message:'Local app connection lost. Restart the demo launcher if needed.'};frame={points:[],blobs:[],touches:[]};renderState();};
}
init().catch(error=>toast(error.message,true));
