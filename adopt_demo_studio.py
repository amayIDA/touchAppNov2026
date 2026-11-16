from pathlib import Path
p=Path('lidar_touch/studio.py');s=p.read_text(encoding='utf-8-sig').replace('from engine import LidarWorker,','from engine import SdkLidarWorker as LidarWorker,')
s=s.replace("calibrated=False,verified=False,coverage=[0,0,.7,1] if i==0 else [.3,0,1,1],yaw=0,min_mm=80,max_mm=8000,foreground_mm=12,cluster_gap_mm=35,max_blob_mm=100,min_points=1,quality=1", "calibrated=False,verified=False,precision_verified=False,background_revision=0,coverage=[0,0,1,1],yaw=0,min_mm=50,max_mm=20000,foreground_mm=60,cluster_gap_mm=100,max_radius_mm=160,min_points=3,quality=1")
s=s.replace("roi=roi,matrix=h.tolist()", "roi=[],matrix=None",1)
s=s.replace('return dict(version=1,','return dict(version=1,detection_revision=2,',1)
s=s.replace(' for s in d[\'sensors\']:', ''' if d.get('detection_revision')!=2:
  backup=Path(str(path)+'.before-demo-sdk.json')
  if not backup.exists():backup.write_bytes(Path(path).read_bytes())
  d['detection_revision']=2
  for sensor in d['sensors']:
   sensor.update(matrix=None,roi=[],calibrated=False,verified=False,precision_verified=False,background_revision=0,coverage=[0,0,1,1],foreground_mm=60,cluster_gap_mm=100,max_radius_mm=160,min_points=3,min_mm=50,max_mm=20000)
 for s in d['sensors']:''',1)
s=s.replace('if background.exists():','if background.exists() and proc.settings.get(\'background_revision\')==2:')
a=s.index('class TouchCanvas(QWidget):');b=s.index('\nclass Studio(',a)
s=s[:a]+'''class TouchCanvas(QWidget):
 def __init__(self,owner,calibrate=None,refine=False):
  super().__init__();self.owner=owner;self.sensor=calibrate;self.refine=refine;self.phase='fit';self.index=0;self.world=[];self.targets=[];self.samples=[];self.armed=False;self.clear_since=None;self.progress=0;self.note='Remove your hand to begin';self.sample_frame=0;self.anchor=None;self.committed=False
  self.original=None
  if calibrate is not None:
   proc=owner.processors[calibrate];self.original=(copy.deepcopy(proc.settings),None if proc.matrix is None else proc.matrix.copy())
  self.setWindowTitle('Guided touch calibration' if calibrate is not None else 'Live touch test');self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
  self.setGeometry(owner.target_screen().geometry());self.showFullScreen()
  if calibrate is not None:self.targets=self.grid(False)
  self.timer=QTimer(self);self.timer.timeout.connect(self.tick);self.timer.start(33)
 def grid(self,validation):
  l,t,r,b=self.owner.processors[self.sensor].settings['coverage']
  if self.refine:
   uv=[(.25,.25),(.75,.25),(.5,.6),(.25,.75),(.75,.75)] if validation else [(x,y) for y in (.1,.5,.9) for x in (.1,.5,.9)]
  else:uv=[(.5,.5)] if validation else [(.08,.08),(.92,.08),(.92,.92),(.08,.92)]
  return [np.array([l+x*(r-l),t+y*(b-t)]) for x,y in uv]
 def tick(self):
  if self.sensor is not None:self.calibration_tick()
  self.update()
 def calibration_tick(self):
  proc=self.owner.processors[self.sensor];now=time.monotonic()
  if now-proc.last_frame>.8:self.note='Waiting for fresh SDK scans…';self.samples=[];return
  blobs=proc.clusters
  if not self.armed:
   if blobs:self.clear_since=None
   else:
    if self.clear_since is None:self.clear_since=now
    if now-self.clear_since>.35:self.armed=True;self.samples=[];self.anchor=None
   self.note='Remove your hand from the scan plane before the next target';return
  # Bootstrap exactly like the supplied demo: a single raw hand cluster, with
  # no projection, guessed rectangle, or proximity-to-screen-target filter.
  if len(blobs)!=1:
   self.samples=[];self.anchor=None;self.progress=0
   self.note='Touch the target with one hand' if not blobs else f'{len(blobs)} objects detected — leave only one hand in the scan plane'
   return
  if proc.last_frame==self.sample_frame:return
  self.sample_frame=proc.last_frame;point=blobs[0]['world']
  if self.anchor is None or np.linalg.norm(point-self.anchor)>25:
   self.anchor=point.copy();self.samples=[]
  self.samples.append((now,point.copy()));duration=now-self.samples[0][0]
  self.progress=min(duration/.9,1);self.note='Hold still… raw hand detected'
  if duration>=.9 and len(self.samples)>=8:
   median=np.median([s[1] for s in self.samples],axis=0)
   self.world.append(median.tolist());self.armed=False;self.clear_since=None;self.samples=[];self.anchor=None;self.progress=0;self.index+=1
   if self.index>=len(self.targets):self.finish_phase()
 def finish_phase(self):
  proc=self.owner.processors[self.sensor];scale=np.array([self.width(),self.height()])
  try:
   if self.phase=='fit':
    if not self.refine:
     points=np.asarray(self.world);edges=np.roll(points,-1,axis=0)-points
     crosses=edges[:,0]*np.roll(edges,-1,axis=0)[:,1]-edges[:,1]*np.roll(edges,-1,axis=0)[:,0]
     if not (np.all(crosses>100) or np.all(crosses< -100)):raise ValueError('Corner captures cross or overlap. Repeat TL → TR → BR → BL.')
    h=fit_homography(self.world,self.targets);errors=np.linalg.norm((project(h,self.world)-self.targets)*scale,axis=1)
    if self.refine and errors.max()>20:raise ValueError(f'Inconsistent captures: maximum fit error {errors.max():.1f}px. Repeat calibration.')
    proc.matrix=h
    self.pending_fit=float(np.sqrt(np.mean(errors**2)))
    self.phase='verify';self.world=[];self.targets=self.grid(True);self.index=0;self.note='Now verify the center' if not self.refine else 'Independent accuracy checks';return
   delta=project(proc.matrix,self.world)-self.targets
   errors=np.linalg.norm(delta*scale,axis=1);rms=float(np.sqrt(np.mean(errors**2)));maximum=float(errors.max());fraction=float(np.linalg.norm(delta,axis=1).max())
   passed=maximum<=self.owner.accuracy.value() if self.refine else fraction<.08
   if not passed:raise ValueError((f'Precision check missed by {maximum:.1f}px.' if self.refine else f'Center check missed by {fraction*100:.1f}% of the screen.')+' Check target captures and repeat. Previous calibration retained.')
   roi=project(np.linalg.inv(proc.matrix),[[0,0],[1,0],[1,1],[0,1]]).tolist()
   proc.settings.update(matrix=proc.matrix.tolist(),roi=roi,calibrated=True,verified=True,precision_verified=self.refine,calibration_method='9-point-refinement' if self.refine else 'demo-four-corners-center',fit_rms_px=self.pending_fit,validation_rms_px=rms,validation_max_px=maximum,center_error_fraction=fraction,validation_resolution=[self.width(),self.height()])
   self.committed=True;self.owner.save_profile(silent=True)
   detail=f'precision RMS {rms:.1f}px, max {maximum:.1f}px' if self.refine else f'center error {fraction*100:.1f}% ({maximum:.1f}px)'
   self.owner.message(f'{proc.settings["name"]}: alignment saved — {detail}. Test touches; precise 9-point refinement is available separately.')
   self.close()
  except Exception as exc:self.owner.message(str(exc));self.close()
 def paintEvent(self,e):
  p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.fillRect(self.rect(),QColor('#061629'));p.setPen(QColor('#d8f5ff'));p.setFont(QFont('Segoe UI',19,QFont.Weight.Bold))
  if self.sensor is None:title='Live touch test — Esc to close'
  else:
   step=self.index+1 if self.phase=='fit' else (9 if self.refine else 4)+self.index+1
   title=f'{self.owner.processors[self.sensor].settings["name"]} • '+('Precision refinement' if self.refine else 'Demo calibration')+f' • {step}/{14 if self.refine else 5}'
  p.drawText(QRectF(20,15,self.width()-40,50),Qt.AlignmentFlag.AlignCenter,title)
  p.setFont(QFont('Segoe UI',13));p.drawText(QRectF(20,self.height()-75,self.width()-40,55),Qt.AlignmentFlag.AlignCenter|Qt.TextFlag.TextWordWrap,self.note if self.sensor is not None else 'Orange circles are actual fused lidar touches. TUIO output is paused during this test.')
  if self.sensor is not None and self.index<len(self.targets):
   q=self.targets[self.index]*[self.width(),self.height()];point=QPointF(*q)
   p.setBrush(QColor(60,190,240,25));p.setPen(QPen(QColor('#39c7ff'),3));p.drawEllipse(point,28,28)
   p.drawLine(point-QPointF(42,0),point+QPointF(42,0));p.drawLine(point-QPointF(0,42),point+QPointF(0,42))
   p.setPen(QPen(QColor('#ffe28c'),6));p.drawArc(QRectF(point.x()-35,point.y()-35,70,70),90*16,-round(self.progress*360*16))
  elif self.sensor is None:
   for uv in [(.1,.1),(.9,.1),(.5,.5),(.1,.9),(.9,.9)]:
    q=QPointF(uv[0]*self.width(),uv[1]*self.height());p.setPen(QPen(QColor('#31536a'),1));p.drawEllipse(q,15,15)
   for sid,uv in self.owner.touches.items():
    q=QPointF(uv[0]*self.width(),uv[1]*self.height());p.setPen(QPen(QColor('#ffb15e'),2));p.setBrush(QColor(255,177,94,65));p.drawEllipse(q,15,15);p.drawText(q+QPointF(20,0),str(sid))
  p.end()
 def keyPressEvent(self,e):
  if e.key()==Qt.Key.Key_Escape:self.close()
 def closeEvent(self,e):
  self.timer.stop()
  if self.sensor is not None and not self.committed:
   proc=self.owner.processors[self.sensor];old,matrix=self.original;proc.settings.clear();proc.settings.update(old);proc.matrix=matrix
  self.owner.canvas=None;self.owner.output.setChecked(False);e.accept()
''' +s[b:]
s=s.replace('1 Connect • 2 Measure screen & align scan planes • 3 Learn empty scene • 4 Calibrate each lidar • 5 Enable TUIO','1 Connect SDK • 2 Record empty background • 3 Touch four corners + center • 4 Test • 5 Enable TUIO')
s=s.replace("  a.addWidget(QLabel('Physical touch-area width (mm)'));self.width_mm=QSpinBox();self.width_mm.setRange(200,20000);self.width_mm.setValue(self.profile['width_mm']);a.addWidget(self.width_mm)","  self.width_mm=QSpinBox();self.width_mm.setRange(200,20000);self.width_mm.setValue(self.profile['width_mm']);self.width_mm.hide()")
s=s.replace("  a.addWidget(QLabel('Physical touch-area height (mm)'));self.height_mm=QSpinBox();self.height_mm.setRange(200,20000);self.height_mm.setValue(self.profile['height_mm']);a.addWidget(self.height_mm)","  self.height_mm=QSpinBox();self.height_mm.setRange(200,20000);self.height_mm.setValue(self.profile['height_mm']);self.height_mm.hide()")
s=s.replace("  mounts=QPushButton('Apply bottom-left / bottom-right layout');mounts.clicked.connect(self.apply_layout);a.addWidget(mounts)","")
s=s.replace("The initial 3000 × 1700 mm values are examples: enter your measured visible area. Mount both scan planes parallel to the screen, just in front of it. A 2D lidar cannot measure finger-to-glass depth; physical plane alignment determines when a touch is detected.","No guessed dimensions or screen boundary are required. This uses the SDK connection and five-target calibration from your demo. Mount the scan planes just in front of and parallel to the screen. Close FrameGrabber and other direct controllers first.")
s=s.replace("tuning=QWidget();b=QVBoxLayout(tuning);tabs.addTab(tuning,'Calibrate')","tuning=QWidget();b=QVBoxLayout(tuning);tuning_scroll=QScrollArea();tuning_scroll.setWidgetResizable(True);tuning_scroll.setWidget(tuning);tabs.addTab(tuning_scroll,'Calibrate')")
s=s.replace("self.threshold.setRange(2,100)","self.threshold.setRange(10,500)")
s=s.replace("self.blob.setRange(10,250);b.addWidget(QLabel('Maximum fingertip/hand cluster width (mm)'))","self.blob.setRange(20,500);b.addWidget(QLabel('Maximum detected hand radius (mm)'))")
s=s.replace("self.minimum.setRange(1,20)","self.minimum.setRange(1,30)")
s=s.replace("Learn empty scene (both, ~5 seconds)","Record empty background (both, 2 seconds)")
s=s.replace("Finger calibration + accuracy validation","Guided calibration: four corners + center")
s=s.replace("self.calibrate.clicked.connect(self.begin_calibration);b.addWidget(self.calibrate)","self.calibrate.clicked.connect(self.begin_calibration);b.addWidget(self.calibrate)\n  self.refine_button=QPushButton('Optional: precision refinement (9 + 5)');self.refine_button.clicked.connect(self.begin_refinement);b.addWidget(self.refine_button)\n  self.raw_label=QLabel('Raw hand detections: 0');self.raw_label.setWordWrap(True);b.addWidget(self.raw_label)")
s=s.replace("Clear the touch area while learning. During calibration, hold one fingertip at each target, then lift. Each lidar gets 9 calibration points and 5 independent validation points. If the approximate boundary is wrong, pick TL → TR → BR → BL on the scan.","Record with the scan plane empty. Then run the same five-target flow as your demo: TL → TR → BR → BL → center. Hold one hand still until captured; fully remove it between targets. Orange raw hand detections work before any mapping. Refine precision later if needed.")
s=s.replace("Sensors already scanning are left running.","Sensors already scanning are left running.")
s=s.replace("self.zoom.setValue(5)","self.zoom.setValue(8)")
s=s.replace("fit=QPushButton('Fit screen boundary');fit.clicked.connect(lambda:self.zoom.setValue(min(30,max(1,max(self.width_mm.value(),self.height_mm.value())*1.4/1000))))", "fit=QPushButton('Fit live scan');fit.clicked.connect(self.fit_view)")
s=s.replace("s.get('foreground_mm',12)","s.get('foreground_mm',60)")
s=s.replace("self.blob.setValue(s.get('max_blob_mm',100));self.minimum.setValue(s.get('min_points',1))","self.blob.setValue(s.get('max_radius_mm',160));self.minimum.setValue(s.get('min_points',3))")
s=s.replace("max_blob_mm=self.blob.value()","max_radius_mm=self.blob.value()")
s=s.replace(" def apply_layout(self):"," def fit_view(self):\n  proc=self.processors[self.selected()]\n  if len(proc.points):self.zoom.setValue(min(30,max(1,float(np.percentile(np.abs(proc.points),95))*2.4/1000)))\n  self.scanview.update()\n def apply_layout(self):")
s=s.replace(" def begin_calibration(self):"," def begin_refinement(self):\n  self.begin_calibration(refine=True)\n def begin_calibration(self,checked=False,refine=False):")
s=s.replace("self.canvas=TouchCanvas(self,self.selected())","self.canvas=TouchCanvas(self,self.selected(),refine=refine)")
# After calibration, crop output, not raw foreground used for bootstrapping.
s=s.replace("if np.isfinite(uv).all() and (uv>=0).all() and (uv<=1).all() and (not self.output.isChecked() or self.usable(proc)):detections.append((i,uv))", "l,t,r,b=proc.settings.get('coverage',[0,0,1,1])\n      if np.isfinite(uv).all() and l<=uv[0]<=r and t<=uv[1]<=b and (not self.output.isChecked() or self.usable(proc)):detections.append((i,uv))")
s=s.replace("  proc=self.processors[self.selected()];s=proc.settings\n  self.calibration_label", "  proc=self.processors[self.selected()];s=proc.settings\n  self.raw_label.setText(f'Raw hand detections: {len(proc.clusters)} — available before calibration')\n  self.calibration_label")
s=s.replace("('Validated' if s.get('verified') else 'Calibrated — validation required' if s.get('calibrated') else 'Not calibrated')", "('Precision validated' if s.get('precision_verified') else 'Demo alignment ready (optional precision refinement available)' if s.get('verified') else 'Not calibrated — raw detections can still be captured')")
s=s.replace("Only calibrated, validated and fresh sensors contribute.","Only aligned, checked and fresh sensors contribute.")
s=s.replace("sensors validated and ready","sensors aligned and ready")
p.write_text(s,encoding='utf-8')
