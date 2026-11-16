// TUIO 1.1 /tuio/2Dcur over OSC/UDP. Implements alive/set/fseq lifecycle.
function oscMessages(buffer,depth=0) {
  if(depth>8)throw Error('OSC nesting too deep');
  if(buffer.length<4)throw Error('Truncated OSC packet');
  if(buffer.subarray(0,8).toString()==='#bundle\0') {
    const result=[];let offset=16;
    while(offset<buffer.length){if(offset+4>buffer.length)throw Error('Truncated OSC bundle');const size=buffer.readInt32BE(offset);offset+=4;if(size<1||offset+size>buffer.length)throw Error('Invalid OSC bundle');result.push(...oscMessages(buffer.subarray(offset,offset+size),depth+1));offset+=size;}
    return result;
  }
  let offset=0;
  const string=()=>{const end=buffer.indexOf(0,offset);if(end<0)throw Error('Invalid OSC string');const s=buffer.toString('utf8',offset,end);offset=(end+4)&~3;if(offset>buffer.length)throw Error('Truncated OSC padding');return s;};
  const address=string(),types=string(),args=[];
  if(types[0]!==',')throw Error('Invalid OSC type tags');
  for(const type of types.slice(1)){
    if(type==='s')args.push(string());
    else if(type==='i'||type==='f'){if(offset+4>buffer.length)throw Error('Truncated OSC number');args.push(type==='i'?buffer.readInt32BE(offset):buffer.readFloatBE(offset));offset+=4;}
    else throw Error('Unsupported OSC type');
  }
  return [{address,args}];
}
class TuioTracker {
  constructor(){this.points=new Map();this.pending=new Map();this.alive=null;this.sequence=null;this.lastAccepted=0;}
  feed(packet,now=Date.now()){
    // A sender restart resets its frame counter. Forget the old session after
    // an idle gap so it cannot suppress every frame from the restarted source.
    if(this.lastAccepted&&now-this.lastAccepted>2500){this.points.clear();this.pending.clear();this.alive=null;this.sequence=null;}
    let result=null;
    for(const {address,args} of oscMessages(packet)){
      if(address!=='/tuio/2Dcur')continue;
      if(args[0]==='set'&&Number.isInteger(args[1])&&Number.isFinite(args[2])&&Number.isFinite(args[3]))this.pending.set(args[1],{id:args[1],x:args[2]*1000,y:args[3]*1000,count:1});
      if(args[0]==='alive')this.alive=new Set(args.slice(1));
      if(args[0]==='fseq'){
        const seq=args[1];
        const accepted=Number.isInteger(seq)&&(seq===-1||this.sequence===null||seq>this.sequence||(this.sequence>2147483000&&seq<1000));
        if(accepted){
          for(const [id,p] of this.pending)this.points.set(id,p);
          if(this.alive)for(const id of this.points.keys())if(!this.alive.has(id))this.points.delete(id);
          if(seq!==-1)this.sequence=seq;
          result=[...this.points.values()];
          this.lastAccepted=now;
        }
        this.pending.clear();this.alive=null;
      }
    }
    return result;
  }
}
module.exports={oscMessages,TuioTracker};
