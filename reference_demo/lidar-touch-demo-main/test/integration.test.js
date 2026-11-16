const test=require('node:test'),assert=require('node:assert/strict');
const {spawn}=require('node:child_process'),dgram=require('node:dgram'),os=require('node:os'),path=require('node:path'),fs=require('node:fs');
function str(s){const b=Buffer.alloc(Math.ceil((Buffer.byteLength(s)+1)/4)*4);b.write(s);return b;}
function message(args){return Buffer.concat([str('/tuio/2Dcur'),str(','+args.map(a=>typeof a==='string'?'s':Number.isInteger(a)?'i':'f').join('')),...args.map(a=>{if(typeof a==='string')return str(a);const b=Buffer.alloc(4);Number.isInteger(a)?b.writeInt32BE(a):b.writeFloatBE(a);return b;})]);}
function packet(messages){return Buffer.concat([str('#bundle'),Buffer.alloc(8),...messages.map(a=>{const body=message(a),size=Buffer.alloc(4);size.writeInt32BE(body.length);return Buffer.concat([size,body]);})]);}
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
test('local server receives TUIO, applies verified calibration, rejects bad calibration and clears disconnected touches',async t=>{
  const dataDir=fs.mkdtempSync(path.join(os.tmpdir(),'s3-touch-test-'));
  const port=19000+Math.floor(Math.random()*10000),udpPort=port+10000;
  const proc=spawn(process.execPath,['server.js'],{cwd:path.join(__dirname,'..'),env:{...process.env,PORT:String(port),DATA_DIR:dataDir},windowsHide:true,stdio:['pipe','pipe','pipe']});
  const sock=dgram.createSocket('udp4');
  const abort=new AbortController();
  t.after(()=>{abort.abort();sock.close();proc.kill();fs.rmSync(dataDir,{recursive:true,force:true});});
  await new Promise((resolve,reject)=>{proc.stdout.once('data',resolve);proc.once('error',reject);proc.once('exit',code=>reject(Error('Test server exited '+code)));});
  const base=`http://127.0.0.1:${port}`,api=async(route,body)=>{const r=await fetch(base+'/api/'+route,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});return {status:r.status,body:await r.json()};};
  const stream=await fetch(base+'/api/events',{signal:abort.signal}),events=[];
  (async()=>{let text='';try{for await(const chunk of stream.body){text+=Buffer.from(chunk).toString();let end;while((end=text.indexOf('\n\n'))>=0){const block=text.slice(0,end);text=text.slice(end+2);const lines=block.split('\n');events.push({type:lines[0].slice(7),data:JSON.parse(lines[1].slice(6))});}}}catch{}})();
  assert.equal((await api('connect',{transport:'tuio',address:'127.0.0.1',port:udpPort})).status,200);
  const send=async(messages)=>{await new Promise((resolve,reject)=>sock.send(packet(messages),udpPort,'127.0.0.1',error=>error?reject(error):resolve()));await wait(60);};
  await send([['alive',7],['set',7,.25,.75,0,0,0],['fseq',1]]);
  let live=events.filter(e=>e.type==='frame'&&e.data.source==='tuio').at(-1);assert.equal(live.data.touches.length,1);assert.equal(live.data.touches[0].u,.25);
  const corners=[[80,80],[920,80],[920,920],[80,920]],targets=[[.08,.08],[.92,.08],[.92,.92],[.08,.92]];
  assert.equal((await api('check-calibration',{corners,targets,center:[500,500]})).body.ok,true);
  assert.equal((await api('check-calibration',{corners,targets,center:[700,500]})).body.ok,false);
  assert.equal((await api('calibration',{corners,targets})).status,200);
  assert.equal((await api('calibration',{corners:[[0,0],[1,1],[1,0],[0,1]]})).status,400);
  await send([['alive',7],['set',7,.5,.5,0,0,0],['fseq',2]]);
  live=events.filter(e=>e.type==='frame'&&e.data.source==='tuio').at(-1);assert.ok(Math.abs(live.data.touches[0].u-.5)<1e-7);
  await wait(3000);assert.equal((await (await fetch(base+'/api/config')).json()).state.status,'waiting');
  assert.equal(events.filter(e=>e.type==='frame').at(-1).data.touches.length,0);
  assert.equal((await api('disconnect',{})).status,200);
  assert.equal((await (await fetch(base+'/api/config')).json()).state.status,'disconnected');
  assert.deepEqual(JSON.parse(fs.readFileSync(path.join(dataDir,'config.json'))).corners,corners);
});
test('compiled native bridge reports a closed TCP endpoint without pretending to stream',{skip:process.platform!=='win32'},async()=>{
  const proc=spawn(path.join(__dirname,'../bin/lidar-bridge.exe'),['tcp','127.0.0.1','1'],{windowsHide:true,stdio:['pipe','pipe','pipe']});let output='';proc.stdout.on('data',chunk=>output+=chunk);
  const code=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>{proc.kill();reject(Error('Bridge did not time out'));},12000);proc.on('error',reject);proc.on('close',code=>{clearTimeout(timer);resolve(code);});});
  assert.notEqual(code,0);assert.match(output,/"type":"error"/);assert.doesNotMatch(output,/"type":"scan"/);
});
