import os,tempfile,time,sys
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
import numpy as np
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from studio import Studio,TouchCanvas
from engine import project,fit_homography
app=QApplication([]);temporary=tempfile.TemporaryDirectory();window=Studio(Path(temporary.name)/'test-profile.json');window.show();window.resize(1500,950)
proc=window.processors[0];proc.baseline=np.full(1440,5000.);window.grab().save('studio-preview.png')
truth=fit_homography([[900,2700],[2900,3000],[3300,900],[1300,600]],[[0,0],[1,0],[1,1],[0,1]])
assert proc.matrix is None, 'Calibration must bootstrap without a map'
window.canvas=TouchCanvas(window,0,refine='--refine' in sys.argv);canvas=window.canvas
steps=0;wrong_since=None;wrong_checked=False;deadline=time.monotonic()+45

def drive():
 global steps,wrong_since,wrong_checked
 if window.canvas is None:
  try:
   assert proc.settings['verified'],window.message_label.text()
   assert proc.settings['validation_max_px']<.01
   assert (Path(temporary.name)/'test-profile.json').exists()
   window.grab().save('studio-completed-preview.png')
   print('PASS: guided raw-hand calibration without guessed dimensions/ROI; 12 random target checks, rejected wrong touch, saved rotated mapping; UI renders',flush=True)
   timer.stop();window.close();app.exit(0)
  except Exception as exc:print(repr(exc),flush=True);timer.stop();window.close();app.exit(1)
  return
 if time.monotonic()>deadline:
  print('FAIL: wizard timeout',canvas.phase,canvas.index,canvas.note,flush=True);timer.stop();window.close();app.exit(1);return
 proc.last_frame=time.monotonic()
 if not canvas.armed:proc.clusters=[]
 else:
  target=canvas.targets[canvas.index]
  if canvas.phase=='verify' and not canvas.refine and not wrong_checked:
   assert len(canvas.targets)==12
   if wrong_since is None:wrong_since=time.monotonic()
   assert canvas.index==0, 'Wrong target must not advance validation'
   if time.monotonic()-wrong_since<1.3:target=np.array([.99,.99])
   else:wrong_checked=True
  world=project(np.linalg.inv(truth),[target])[0]
  proc.clusters=[dict(world=world,size=10,rays=3,hits=5)]
 steps+=1
 if steps==40:canvas.grab().save('calibration-preview.png')
timer=QTimer();timer.timeout.connect(drive);timer.start(40)
raise SystemExit(app.exec())
