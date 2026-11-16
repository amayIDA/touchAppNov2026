import json,time
from pathlib import Path
from PySide6.QtCore import QCoreApplication,QTimer
from engine import SdkLidarWorker as LidarWorker
app=QCoreApplication([]);workers=[];counts=[0,0];samples=[0,0];devices={};statuses={};started=time.monotonic()
def frame(i,scan):counts[i]+=1;samples[i]+=len(scan)
def device(i,d):devices[i]=d
def status(i,s):statuses[i]=s
for i,ip in enumerate(('192.168.11.2','192.168.11.3')):
 w=LidarWorker(i,ip);w.frame.connect(frame);w.device.connect(device);w.status.connect(status);workers.append(w);w.start()
def finish():
 for w in workers:w.stop()
 for w in workers:w.wait(3500)
 report={'devices':devices,'status':statuses,'full_scans':counts,'samples':samples,'elapsed_seconds':round(time.monotonic()-started,2),'calibrated':False}
 Path('hardware-check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print(json.dumps(report,indent=2),flush=True)
 app.exit(0 if all(c>=10 for c in counts) else 1)
QTimer.singleShot(8000,finish)
raise SystemExit(app.exec())

