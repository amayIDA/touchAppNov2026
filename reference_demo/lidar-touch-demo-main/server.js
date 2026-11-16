const http=require('node:http');
const fs=require('node:fs');
const path=require('node:path');
const {spawn}=require('node:child_process');
const {createInterface}=require('node:readline');
const {TouchEngine,homography}=require('./touch-engine');
const {project}=require('./touch-engine');
const {TuioTracker}=require('./tuio');
const dgram=require('node:dgram');
const ROOT=__dirname, PORT=Number(process.env.PORT||4173);
const configPath=path.join(process.env.DATA_DIR||path.join(ROOT,'data'),'config.json');
let config={transport:'tuio',address:'127.0.0.1',port:3333,baud:1000000,threshold:60,minPoints:3,maxRadius:160,clusterGap:100,corners:null,targets:null};
try{config={...config,...JSON.parse(fs.readFileSync(configPath,'utf8'))};}catch{}
const engine=new TouchEngine(config), clients=new Set();
let child=null,tuioSocket=null,stopping=null,lastFrame=0,lastScan=0,frameCount=0,hz=0,hzAt=Date.now();
let state={status:'disconnected',message:'Connect your SLAMTEC S3 to begin.',device:null};
let latest={points:[],blobs:[],touches:[],backgroundReady:false,learning:false};
let guidance={active:false};
function broadcast(type,data) {const out=`event: ${type}\ndata: ${JSON.stringify(data)}\n\n`;for(const client of clients){if(client.writableLength>512000){client.destroy();clients.delete(client);}else client.write(out);}}
function setState(status,message){state={...state,status,message};broadcast('state',state);}
function clearFrame(){latest={points:[],blobs:[],touches:[],backgroundReady:false,learning:false};broadcast('frame',{...latest,hz:0,timestamp:Date.now()});}
function save(){fs.mkdirSync(path.dirname(configPath),{recursive:true});fs.writeFileSync(configPath,JSON.stringify(config,null,2));}
async function disconnect(){
  if(stopping) return stopping;
  if(tuioSocket){const oldSocket=tuioSocket;tuioSocket=null;await new Promise(resolve=>oldSocket.close(resolve));}
  const old=child;child=null;engine.reset();clearFrame();state.device=null;
  if(!old){setState('disconnected','Sensor disconnected.');return;}
  stopping=new Promise(resolve=>{
    const timer=setTimeout(()=>old.kill(),4000);
    old.once('close',()=>{clearTimeout(timer);resolve();});
    if(old.exitCode!==null){clearTimeout(timer);resolve();return;}
    old.stdin.write('stop\n',()=>{});
  });
  await stopping;stopping=null;setState('disconnected','Sensor disconnected.');
}
async function connect(input){
  if(!['tcp','udp','serial','tuio'].includes(input.transport))throw Error('Choose a supported connection.');
  if(typeof input.address!=='string'||!input.address.trim()||input.address.length>150)throw Error('Enter the sensor IP address or COM port.');
  const serial=input.transport==='serial',port=Number(serial?input.baud:input.port);
  if(!Number.isInteger(port)||port<1||port>(serial?4000000:65535))throw Error('Enter a valid port or baud rate.');
  const executable=path.join(ROOT,'bin','lidar-bridge.exe');
  if(input.transport!=='tuio'&&!fs.existsSync(executable))throw Error('The sensor bridge needs to be built. Run npm run build:bridge.');
  const changed=config.transport!==input.transport||config.address!==input.address.trim()||(!serial&&config.port!==port);
  await disconnect();config={...config,...(changed?{corners:null,targets:null}:{}),...{transport:input.transport,address:input.address.trim(),port:serial?config.port:port,baud:serial?port:config.baud}};save();broadcast('config',config);
  engine.setConfig(config);lastScan=0;frameCount=0;hz=0;hzAt=Date.now();setState('connecting','Opening S3 connection…');
  if(config.transport==='tuio'){
    const tracker=new TuioTracker(),sock=dgram.createSocket('udp4');tuioSocket=sock;
    sock.on('error',error=>{if(tuioSocket===sock){tuioSocket=null;sock.close();setState('error',error.message);clearFrame();}});
    sock.on('message',packet=>{
      if(tuioSocket!==sock)return;
      let blobs;try{blobs=tracker.feed(packet);}catch{return;}if(blobs===null)return;
      const now=Date.now();lastScan=now;frameCount++;
      if(now-hzAt>=1000){hz=Math.round(frameCount*10000/(now-hzAt))/10;hzAt=now;frameCount=0;}
      if(state.status!=='streaming')setState('streaming','Live touches from SLAMTEC Frame Grabber.');
      const touches=blobs.map(p=>{const [u,v]=engine.h?project(engine.h,p.x,p.y):[p.x/1000,p.y/1000];return {...p,u,v};}).filter(p=>p.u>=0&&p.u<=1&&p.v>=0&&p.v<=1);
      latest={points:blobs.map(p=>[p.x,p.y]),blobs,touches,backgroundReady:true,learning:false,source:'tuio'};
      broadcast('frame',{...latest,hz,timestamp:now});
    });
    await new Promise((resolve,reject)=>{sock.once('error',reject);sock.bind(port,'127.0.0.1',resolve);});
    setState('waiting',`Listening on local TUIO port ${port}. Enable Multitouch → TUIO in Frame Grabber.`);return;
  }
  const proc=spawn(executable,[config.transport,config.address,String(port)],{windowsHide:true,stdio:['pipe','pipe','pipe']});child=proc;
  proc.stdin.on('error',()=>{});
  let detail='';proc.stderr.on('data',chunk=>{detail=(detail+chunk).slice(-1000);});
  proc.on('error',error=>{if(child===proc){setState('error',error.message);child=null;clearFrame();}});
  proc.on('close',code=>{if(child===proc){child=null;engine.reset();clearFrame();if(state.status!=='error')setState('error',`Sensor stopped (${code}). ${detail||'Check power and network settings, then reconnect.'}`);}});
  const lines=createInterface({input:proc.stdout});
  lines.on('line',line=>{
    if(child!==proc)return;
    let msg;try{msg=JSON.parse(line);}catch{return;}
    if(msg.type==='error'){setState('error',msg.message);clearFrame();return;}
    if(msg.type==='device'){state.device=msg;broadcast('state',state);}
    if(msg.type==='scan'&&Array.isArray(msg.points)){
      const now=Date.now();lastScan=now;frameCount++;
      if(now-hzAt>=1000){hz=Math.round(frameCount*10000/(now-hzAt))/10;hzAt=now;frameCount=0;}
      if(state.status!=='streaming')setState('streaming','Receiving live S3 scans.');
      latest=engine.process(msg.points,now);
      if(now-lastFrame>33){broadcast('frame',{...latest,hz,timestamp:now});lastFrame=now;}
    }
  });
}
const staleTimer=setInterval(()=>{if((child||tuioSocket)&&state.status==='streaming'&&Date.now()-lastScan>(tuioSocket?2500:1500)){engine.tracks=[];clearFrame();if(tuioSocket)setState('waiting','TUIO receiver ready. Waiting for the next detected hand; Frame Grabber may stay silent while the surface is empty.');else setState('stale','Input interrupted. Check sensor power and network.');}},500);
function json(res,code,body){res.writeHead(code,{'Content-Type':'application/json','Cache-Control':'no-store'});res.end(JSON.stringify(body));}
const server=http.createServer(async(req,res)=>{
  const url=new URL(req.url,'http://localhost');
  if(req.method==='GET'&&url.pathname==='/api/events'){
    res.writeHead(200,{'Content-Type':'text/event-stream','Cache-Control':'no-cache','Connection':'keep-alive'});
    res.write(`event: state\ndata: ${JSON.stringify(state)}\n\nevent: frame\ndata: ${JSON.stringify({...latest,hz,timestamp:Date.now()})}\n\nevent: guidance\ndata: ${JSON.stringify(guidance)}\n\n`);
    clients.add(res);req.on('close',()=>clients.delete(res));return;
  }
  if(req.method==='GET'&&url.pathname==='/api/config')return json(res,200,{config,state});
  if(req.method==='POST'&&url.pathname.startsWith('/api/')){
    // Only the local operator may control the hardware. A separate display
    // tab on this PC shares the same read-only event stream.
    if(req.headers.origin && req.headers.origin!==`http://${req.headers.host}`)return json(res,403,{error:'Open the app directly on this PC.'});
    try{
      let body='';for await(const chunk of req){body+=chunk;if(body.length>20000)throw Error('Request too large');}
      const input=body?JSON.parse(body):{};
      if(url.pathname==='/api/connect'){await connect(input);return json(res,200,{ok:true});}
      if(url.pathname==='/api/disconnect'){await disconnect();return json(res,200,{ok:true});}
      if(url.pathname==='/api/guidance'){
        if(typeof input.active!=='boolean')throw Error('Invalid calibration state.');
        guidance=input.active?{active:true,step:Math.max(0,Math.min(4,Number(input.step)||0)),progress:Math.max(0,Math.min(1,Number(input.progress)||0)),message:String(input.message||'Hold your hand on the target.').slice(0,200)}:{active:false};
        broadcast('guidance',guidance);return json(res,200,{ok:true});
      }
      if(url.pathname==='/api/check-calibration'){
        const h=homography(input.corners,input.targets||undefined);
        if(!Array.isArray(input.center)||input.center.length!==2||input.center.some(v=>!Number.isFinite(v)))throw Error('A centre check is required.');
        const [u,v]=project(h,...input.center),error=Math.hypot(u-.5,v-.5);
        return json(res,200,{ok:error<.08,error,position:[u,v]});
      }
      if(url.pathname==='/api/background'){
        if(config.transport==='tuio')throw Error('Frame Grabber handles touch detection in TUIO mode. You can start guided calibration directly.');
        if(state.status!=='streaming')throw Error('Connect the sensor and wait for live scans first.');
        engine.learn();return json(res,200,{ok:true});
      }
      if(url.pathname==='/api/calibration'){
        if(input.corners!==null)homography(input.corners,input.targets||undefined);
        config={...config,corners:input.corners,targets:input.targets||null};engine.setConfig({...config,targets:config.targets||undefined});save();broadcast('config',config);return json(res,200,{ok:true});
      }
      if(url.pathname==='/api/settings'){
        const updates={};
        for(const [key,lo,hi] of [['threshold',10,500],['minPoints',1,30],['maxRadius',20,500],['clusterGap',20,400]]){
          if(input[key]!==undefined){const v=Number(input[key]);if(!Number.isFinite(v)||v<lo||v>hi)throw Error(`Invalid ${key}`);updates[key]=v;}
        }
        config={...config,...updates};engine.setConfig(config);save();return json(res,200,{ok:true});
      }
      return json(res,404,{error:'Unknown action'});
    }catch(error){return json(res,400,{error:error.message});}
  }
  const files={'/':'index.html','/index.html':'index.html','/app.js':'app.js','/gallery.js':'gallery.js','/style.css':'style.css','/pictures/desert.svg':'pictures/desert.svg','/pictures/mountains.svg':'pictures/mountains.svg','/pictures/ocean.svg':'pictures/ocean.svg'};
  const file=files[url.pathname];if(!file){res.writeHead(404);res.end('Not found');return;}
  res.writeHead(200,{'Content-Type':file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':file.endsWith('.svg')?'image/svg+xml':'text/html','Cache-Control':'no-store'});
  fs.createReadStream(path.join(ROOT,'public',file)).pipe(res);
});
server.listen(PORT,'127.0.0.1',()=>console.log(`S3 Touch Studio is ready: http://localhost:${server.address().port}`));
async function closeServer(){clearInterval(staleTimer);await disconnect();for(const c of clients)c.end();await new Promise(resolve=>server.close(resolve));}
async function shutdown(){await closeServer();process.exit(0);}
if(require.main===module){process.on('SIGINT',shutdown);process.on('SIGTERM',shutdown);}
module.exports={server,connect,closeServer};
