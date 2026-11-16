const test=require('node:test');const assert=require('node:assert/strict');const {TuioTracker,oscMessages}=require('../tuio');
function str(s){const b=Buffer.alloc(Math.ceil((Buffer.byteLength(s)+1)/4)*4);b.write(s);return b;}
function message(args){return Buffer.concat([str('/tuio/2Dcur'),str(','+args.map(a=>typeof a==='string'?'s':Number.isInteger(a)?'i':'f').join('')),...args.map(a=>{if(typeof a==='string')return str(a);const b=Buffer.alloc(4);Number.isInteger(a)?b.writeInt32BE(a):b.writeFloatBE(a);return b;})]);}
function packet(messages){return Buffer.concat([str('#bundle'),Buffer.alloc(8),...messages.map(a=>{const body=message(a),size=Buffer.alloc(4);size.writeInt32BE(body.length);return Buffer.concat([size,body]);})]);}
test('TUIO cursor updates preserve unchanged alive cursors and remove released touches',()=>{
 const t=new TuioTracker();const a=t.feed(packet([['alive',9],['set',9,.25,.75,0,0,0],['fseq',1]]));assert.equal(a.length,1);assert.equal(a[0].x,250);assert.equal(a[0].y,750);
 assert.equal(t.feed(packet([['alive',9],['fseq',2]])).length,1);
 assert.equal(t.feed(packet([['alive'],['fseq',3]])).length,0);
});
test('old sequence cannot resurrect a removed cursor',()=>{
 const t=new TuioTracker();t.feed(packet([['alive'],['fseq',20]]));assert.equal(t.feed(packet([['alive',1],['set',1,.2,.3],['fseq',19]])),null);assert.equal(t.feed(packet([['alive'],['fseq',21]])).length,0);
});
test('redundant sequence -1 is accepted and malformed packets rejected',()=>{
 const t=new TuioTracker();assert.equal(t.feed(packet([['alive',1],['set',1,.5,.5],['fseq',-1]])).length,1);assert.throws(()=>oscMessages(Buffer.from('bad')));const invalid=Buffer.concat([str('#bundle'),Buffer.alloc(8),Buffer.from([255,255,255,255])]);assert.throws(()=>oscMessages(invalid));
});
test('a restarted sender recovers after an idle gap despite its frame counter resetting',()=>{
 const t=new TuioTracker();t.feed(packet([['alive',9],['set',9,.25,.75],['fseq',900]]),1000);
 const next=t.feed(packet([['alive',1],['set',1,.5,.5],['fseq',0]]),4000);
 assert.equal(next.length,1);assert.equal(next[0].id,1);assert.equal(next[0].x,500);
});
