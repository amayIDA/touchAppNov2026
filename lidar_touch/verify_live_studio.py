import os,tempfile,time,json
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from studio import Studio
app=QApplication([]);tmp=tempfile.TemporaryDirectory();w=Studio(Path(tmp.name)/'live-check.json');w.show();w.connect_sensors()
counts=[0,0]
for worker in w.workers.values():worker.frame.connect(lambda i,scan:counts.__setitem__(i,counts[i]+1))
def finish():
 now=time.monotonic();report={'frames':counts,'status':w.statuses,'fresh':[now-p.last_frame<.5 for p in w.processors],'valid_points':[len(p.points) for p in w.processors]}
 print(json.dumps(report),flush=True);w.grab().save('live-scan-preview.png');passed=all(report['fresh']) and all(n>20 for n in counts)
 w.close();app.exit(0 if passed else 1)
QTimer.singleShot(15000,finish)
raise SystemExit(app.exec())
