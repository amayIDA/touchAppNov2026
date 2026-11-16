const BINS = 1440;
function solve(matrix, rhs) {
  const m = matrix.map((row, i) => [...row, rhs[i]]), n = rhs.length;
  for (let col = 0; col < n; col++) {
    let pivot = col;
    for (let r = col + 1; r < n; r++) if (Math.abs(m[r][col]) > Math.abs(m[pivot][col])) pivot = r;
    if (Math.abs(m[pivot][col]) < 1e-9) throw Error('Corners do not form a valid screen. Capture four separate corners in order.');
    [m[pivot], m[col]] = [m[col], m[pivot]];
    const d = m[col][col];
    for (let j = col; j <= n; j++) m[col][j] /= d;
    for (let r = 0; r < n; r++) if (r !== col) {
      const f = m[r][col];
      for (let j = col; j <= n; j++) m[r][j] -= f * m[col][j];
    }
  }
  return m.map(row => row[n]);
}
function homography(corners, targets=[[0,0],[1,0],[1,1],[0,1]]) {
  if (!Array.isArray(corners) || corners.length !== 4 || corners.some(p => !Array.isArray(p) || p.length !== 2 || p.some(v => !Number.isFinite(v) || Math.abs(v) > 50000))) throw Error('Four valid corner coordinates are required.');
  const crosses = corners.map((a, i) => { const b = corners[(i+1)%4], c = corners[(i+2)%4]; return (b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0]); });
  if (!crosses.every(v=>v>100) && !crosses.every(v=>v< -100)) throw Error('Corners must surround the screen in order: top left, top right, bottom right, bottom left.');
  if(!Array.isArray(targets)||targets.length!==4||targets.some(p=>!Array.isArray(p)||p.length!==2||p.some(v=>!Number.isFinite(v)||v<0||v>1)))throw Error('Invalid calibration targets.');
  const matrix=[], rhs=[];
  corners.forEach(([x,y], i) => { const [u,v]=targets[i]; matrix.push([x,y,1,0,0,0,-u*x,-u*y],[0,0,0,x,y,1,-v*x,-v*y]); rhs.push(u,v); });
  return solve(matrix,rhs);
}
function project(h, x, y) {
  const w=h[6]*x+h[7]*y+1;
  return [(h[0]*x+h[1]*y+h[2])/w,(h[3]*x+h[4]*y+h[5])/w];
}
class TouchEngine {
  constructor(config={}) { this.config=config; this.baseline=null; this.capture=null; this.tracks=[]; this.nextId=1; this.setConfig(config); }
  setConfig(config) { this.h=config.corners ? homography(config.corners,config.targets||undefined) : null; this.config=config; this.tracks=[]; }
  learn() { this.capture={ start:Date.now(), frames:0, bins:Array.from({length:BINS},()=>[]) }; this.baseline=null; this.tracks=[]; }
  reset() { this.tracks=[]; this.baseline=null; this.capture=null; }
  process(scan, now=Date.now()) {
    const bins=new Float64Array(BINS).fill(Infinity), points=[];
    for (const [angle,d,q] of scan) {
      if (!Number.isFinite(angle)||!Number.isFinite(d)||q<1||d<50||d>20000) continue;
      const a=((angle%360)+360)%360, b=Math.floor(a/360*BINS);
      bins[b]=Math.min(bins[b],d);
      const rad=a*Math.PI/180;
      points.push({x:Math.sin(rad)*d,y:Math.cos(rad)*d,b,d});
    }
    if(this.capture) {
      this.capture.frames++;
      bins.forEach((d,b)=>{ if(Number.isFinite(d)) this.capture.bins[b].push(d); });
      if(now-this.capture.start>=2000 && this.capture.frames>=8) {
        this.baseline=this.capture.bins.map(values=>values.length ? values.sort((a,b)=>a-b)[Math.floor(values.length/2)] : Infinity);
        this.capture=null;
      }
      return {points:points.map(p=>[p.x,p.y]),blobs:[],touches:[],learning:!!this.capture,backgroundReady:!!this.baseline};
    }
    const threshold=this.config.threshold||60;
    const foreground=points.filter(p=>this.baseline && p.d < this.backgroundAt(p.b)-threshold);
    const clusters=[], groups=[]; let group=[];
    for(const p of foreground) {
      const last=group.at(-1);
      if(last && (p.b-last.b>12 || Math.hypot(p.x-last.x,p.y-last.y)>(this.config.clusterGap||100))) { groups.push(group);group=[]; }
      group.push(p);
    }
    if(group.length)groups.push(group);
    if(groups.length>1){const first=groups[0],last=groups.at(-1);if(first[0].b+BINS-last.at(-1).b<12&&Math.hypot(first[0].x-last.at(-1).x,first[0].y-last.at(-1).y)<(this.config.clusterGap||100)){groups[0]=[...last,...first];groups.pop();}}
    for(const group of groups) { if(group.length>=(this.config.minPoints||3)) {
      const x=group.reduce((s,p)=>s+p.x,0)/group.length,y=group.reduce((s,p)=>s+p.y,0)/group.length;
      const radius=Math.max(...group.map(p=>Math.hypot(p.x-x,p.y-y)));
      if(radius<(this.config.maxRadius||160)) clusters.push({x,y,count:group.length});
    } }
    for(let i=0;i<clusters.length;i++) for(let j=clusters.length-1;j>i;j--) if(Math.hypot(clusters[i].x-clusters[j].x,clusters[i].y-clusters[j].y)<80) {
      const a=clusters[i],b=clusters[j],n=a.count+b.count;
      a.x=(a.x*a.count+b.x*b.count)/n;a.y=(a.y*a.count+b.y*b.count)/n;a.count=n;clusters.splice(j,1);
    }
    const candidates=this.h ? clusters.map(p=>{ const [u,v]=project(this.h,p.x,p.y); return {...p,u,v}; }).filter(p=>p.u>=0&&p.u<=1&&p.v>=0&&p.v<=1) : [];
    const used=new Set(), next=[];
    for(const p of candidates.slice(0,20)) {
      let best=null,dist=0.12;
      for(const t of this.tracks) { const d=Math.hypot(t.u-p.u,t.v-p.v); if(!used.has(t.id)&&d<dist){best=t;dist=d;} }
      if(best) {used.add(best.id);next.push({...p,id:best.id,u:best.u*0.35+p.u*0.65,v:best.v*0.35+p.v*0.65});}
      else next.push({...p,id:this.nextId++});
    }
    this.tracks=next;
    return {points:points.map(p=>[p.x,p.y]),blobs:clusters,touches:next,learning:false,backgroundReady:!!this.baseline};
  }
  backgroundAt(b) {
    // Angular jitter must not turn learned walls into touches. Use nearest
    // observed background across neighbouring quarter-degree bins.
    let d=Infinity;
    for(let offset=-2;offset<=2;offset++) d=Math.min(d,this.baseline[(b+offset+BINS)%BINS]);
    return d;
  }
}
module.exports={TouchEngine,homography,project};
