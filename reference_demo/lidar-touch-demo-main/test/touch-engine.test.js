const test=require('node:test');const assert=require('node:assert/strict');
const {TouchEngine,homography,project}=require('../touch-engine');
test('rotated and translated screen maps to its four corners and centre',()=>{
  const angle=.23,c=Math.cos(angle),s=Math.sin(angle);
  const xy=(x,y)=>[x*c-y*s+500,x*s+y*c+1300];
  const corners=[xy(-1000,-600),xy(1000,-600),xy(1000,600),xy(-1000,600)];
  const h=homography(corners);
  corners.forEach((p,i)=>{const q=project(h,...p),expected=[[0,0],[1,0],[1,1],[0,1]][i];assert.ok(Math.hypot(q[0]-expected[0],q[1]-expected[1])<1e-8);});
  const centre=project(h,...xy(0,0));assert.ok(Math.hypot(centre[0]-.5,centre[1]-.5)<1e-8);
});
test('guided inset targets preserve the correct full screen mapping',()=>{
  const corners=[[80,80],[920,80],[920,920],[80,920]],targets=[[.08,.08],[.92,.08],[.92,.92],[.08,.92]];
  const h=homography(corners,targets);assert.deepEqual(project(h,500,500).map(v=>Math.round(v*100)),[50,50]);assert.deepEqual(project(h,0,0).map(v=>Math.round(v*100)),[0,0]);
});
test('invalid and crossed corner configurations are rejected',()=>{
  for(const corners of [[[0,0],[0,0],[0,0],[0,0]],[[0,0],[1000,1000],[1000,0],[0,1000]],[[0,0],[100,0],[200,0],[300,0]]])assert.throws(()=>homography(corners));
});
const baseline=Array.from({length:1440},(_,b)=>[b/4,4000,20]);
function scanWithHand(degrees,distance){return baseline.map(p=>Math.abs(p[0]-degrees)<1?[p[0],distance,20]:p);}
function ready(){const engine=new TouchEngine({corners:[[-2000,500],[2000,500],[2000,3000],[-2000,3000]],minPoints:3});engine.learn();const start=engine.capture.start;for(let i=0;i<11;i++)engine.process(baseline,start+i*250);assert.ok(engine.baseline);return engine;}
test('empty background produces no touches; foreground produces stable touch IDs',()=>{
  const engine=ready();assert.equal(engine.process(baseline).touches.length,0);
  const a=engine.process(scanWithHand(20,1800));assert.equal(a.touches.length,1);assert.ok(a.touches[0].u>0&&a.touches[0].u<1);
  const b=engine.process(scanWithHand(20.25,1800));assert.equal(b.touches[0].id,a.touches[0].id);
  assert.equal(engine.process(baseline).touches.length,0);
});
test('seam-straddling hand is merged before minimum cluster size filtering',()=>{
  const engine=ready();const scan=baseline.map(p=>(p[0]<=.25||p[0]>=359.75)?[p[0],1800,20]:p);
  assert.equal(engine.process(scan).touches.length,1);
});
test('unmapped and out of surface detections never become touches',()=>{
  const engine=ready();assert.equal(engine.process(scanWithHand(100,1800)).touches.length,0);engine.setConfig({});assert.equal(engine.process(scanWithHand(20,1800)).touches.length,0);
});
test('reset requires a fresh empty background after sensor reconnect',()=>{const engine=ready();engine.reset();assert.equal(engine.baseline,null);assert.equal(engine.process(scanWithHand(20,1800)).touches.length,0);});
