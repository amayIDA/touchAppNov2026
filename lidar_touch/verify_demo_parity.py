import json,subprocess,copy
from pathlib import Path
import numpy as np
from engine import SensorProcessor
from studio import default_profile
root=Path(__file__).resolve().parent.parent
reference=root/'reference_demo'/'lidar-touch-demo-main'/'touch-engine.js'
script="""
const {TouchEngine}=require(process.argv[1]);
const base=Array.from({length:1440},(_,b)=>[b/4,4000,20]);
const scans=[base,base.map(p=>Math.abs(p[0]-20)<1?[p[0],1800,20]:p),base.map(p=>(p[0]<=.25||p[0]>=359.75)?[p[0],1800,20]:p),base.map(p=>Math.abs(p[0]-225)<1?[p[0],1300,20]:p)];
const engine=new TouchEngine({minPoints:3});engine.learn();const start=engine.capture.start;for(let i=0;i<11;i++)engine.process(base,start+i*250);
console.log(JSON.stringify(scans.map(scan=>engine.process(scan).blobs)));
"""
expected=json.loads(subprocess.check_output(['node','-e',script,str(reference)],text=True))
base=np.column_stack([np.arange(1440)/4,np.full(1440,4000),np.full(1440,20)])
scans=[base,base.copy(),base.copy(),base.copy()]
scans[1][np.abs(base[:,0]-20)<1,1]=1800
scans[2][(base[:,0]<=.25)|(base[:,0]>=359.75),1]=1800
scans[3][np.abs(base[:,0]-225)<1,1]=1300
proc=SensorProcessor(copy.deepcopy(default_profile()['sensors'][0]));proc.learn(3)
for _ in range(3):proc.update(base)
for case,(scan,wanted) in enumerate(zip(scans,expected)):
 proc.update(scan);assert len(proc.clusters)==len(wanted),(case,len(proc.clusters),len(wanted))
 for actual,other in zip(proc.clusters,wanted):
  assert np.linalg.norm(actual['world']-[other['x'],other['y']])<1e-6,(case,actual,other)
print('PASS: Python raw-blob detection matches supplied JavaScript demo for empty, hand, 360-degree seam and unmapped/outside-old-ROI cases')
