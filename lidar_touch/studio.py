"""Interactive dual Ethernet lidar calibration and TUIO controller."""
import sys,time,json,copy,math,os
from pathlib import Path
import numpy as np
from PySide6.QtCore import Qt,QTimer,QRectF,QPointF,QProcess
from PySide6.QtGui import QPainter,QColor,QPen,QPolygonF,QFont,QFontDatabase
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QLabel,QPushButton,QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox,QCheckBox,QVBoxLayout,QHBoxLayout,QGridLayout,QTabWidget,QGroupBox,QMessageBox,QFileDialog,QScrollArea)
from engine import SdkLidarWorker as LidarWorker,SensorProcessor,TouchTracker,TuioOutput,project,fit_homography
ROOT=Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).parent

def default_profile():
 sensors=[]
 for i in range(2):
  roi=[[0,1700],[3000,1700],[3000,0],[0,0]] if i==0 else [[-3000,1700],[0,1700],[0,0],[-3000,0]]
  h=fit_homography(roi,[[0,0],[1,0],[1,1],[0,1]])
  sensors.append(dict(name='Bottom left' if i==0 else 'Bottom right',ip=f'192.168.11.{i+2}',port=8089,serial='',enabled=True,roi=[],matrix=None,calibrated=False,verified=False,precision_verified=False,background_revision=0,coverage=[0,0,1,1],yaw=0,min_mm=50,max_mm=20000,foreground_mm=60,cluster_gap_mm=100,max_radius_mm=160,min_points=3,quality=1))
 return dict(version=1,detection_revision=2,width_mm=3000,height_mm=1700,screen=0,output_host='127.0.0.1',output_port=3333,merge_px=24,smoothing=.65,accuracy_px=8,sensors=sensors)

def read_profile(path):
 if not Path(path).exists():return default_profile()
 d=json.loads(Path(path).read_text(encoding='utf-8-sig'))
 if d.get('version')!=1 or len(d.get('sensors',[]))!=2:raise ValueError('Invalid dual-lidar profile')
 if d.get('detection_revision')!=2:
  backup=Path(str(path)+'.before-demo-sdk.json')
  if not backup.exists():backup.write_bytes(Path(path).read_bytes())
  d['detection_revision']=2
  for sensor in d['sensors']:
   sensor.update(matrix=None,roi=[],calibrated=False,verified=False,precision_verified=False,background_revision=0,coverage=[0,0,1,1],foreground_mm=60,cluster_gap_mm=100,max_radius_mm=160,min_points=3,min_mm=50,max_mm=20000)
 for s in d['sensors']:
  if s.get('matrix') is not None and np.asarray(s['matrix']).shape!=(3,3):raise ValueError('Invalid calibration matrix')
 return d

class ScanView(QWidget):
 def __init__(self,owner):
  super().__init__();self.owner=owner;self.setMinimumSize(560,420);self.picking=False;self.corners=[];self.setMouseTracking(True)
 def geometry_map(self,sensor=None):
  sensor=self.owner.selected() if sensor is None else sensor
  pane_width=self.width()/2;span=self.owner.zoom.value()*1000;scale=min((pane_width-35)/span,(self.height()-120)/span)
  roi=self.owner.processors[sensor].settings.get('roi',[])
  center=np.mean(roi,axis=0) if roi else np.array([0.,0.])
  return scale,QPointF(pane_width*(sensor+.5)-center[0]*scale,self.height()/2+35+center[1]*scale)
 def to_view(self,p,sensor=None):
  scale,origin=self.geometry_map(sensor);return QPointF(origin.x()+p[0]*scale,origin.y()-p[1]*scale)
 def to_world(self,p):
  scale,origin=self.geometry_map();return np.array([(p.x()-origin.x())/scale,(origin.y()-p.y())/scale])
 def paintEvent(self,e):
  p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.fillRect(self.rect(),QColor('#071526'))
  colors=['#38d5ff','#ff77c8'];now=time.monotonic();pane_width=self.width()/2
  for i,proc in enumerate(self.owner.processors):
   p.save();pane=QRectF(i*pane_width,0,pane_width,self.height());p.setClipRect(pane)
   color=QColor(colors[i]);fresh=now-proc.last_frame<.5;scale,origin=self.geometry_map(i);span=self.owner.zoom.value()*1000
   p.setPen(QPen(QColor('#224059'),1))
   for n in range(-40,41):
    p.drawLine(self.to_view((n*500,-span),i),self.to_view((n*500,span),i));p.drawLine(self.to_view((-span,n*500),i),self.to_view((span,n*500),i))
   p.setPen(QPen(color if fresh else QColor('#526070'),2))
   if len(proc.points):p.drawPoints([self.to_view(pt,i) for pt in proc.points[::max(1,len(proc.points)//3500)]])
   roi=proc.settings.get('roi',[])
   if roi:
    p.setPen(QPen(QColor('#51dbc3'),2));p.setBrush(QColor(41,170,140,18));p.drawPolygon(QPolygonF([self.to_view(pt,i) for pt in roi]))
    for label,point in zip(['TL','TR','BR','BL'],roi):
     q=self.to_view(point,i);p.drawText(q+QPointF(8,-8),label)
   if fresh:
    for blob in proc.clusters:
     q=self.to_view(blob['world'],i);fill=QColor(color);fill.setAlpha(100);p.setBrush(fill);p.setPen(QPen(color,3));p.drawEllipse(q,10,10);p.setPen(QColor('white'));p.drawLine(q-QPointF(4,0),q+QPointF(4,0))
   p.setPen(QPen(color,2));p.drawLine(origin-QPointF(9,0),origin+QPointF(9,0));p.drawLine(origin-QPointF(0,9),origin+QPointF(0,9))
   p.drawText(origin+QPointF(12,18),f'LIDAR {i+1}')
   p.fillRect(QRectF(i*pane_width,0,pane_width,100),QColor('#0b1c2e'))
   p.setPen(color);p.setFont(QFont('Segoe UI',12,QFont.Weight.Bold));p.drawText(QRectF(i*pane_width+12,10,pane_width-24,30),f'Lidar {i+1} — {proc.settings["name"]}')
   p.setFont(QFont('Segoe UI',10));state='LIVE' if fresh else 'NO LIVE SCANS'
   count=len(proc.clusters) if fresh else 0
   p.drawText(QRectF(i*pane_width+12,42,pane_width-24,55),Qt.TextFlag.TextWordWrap,f'{state} • {count} detected contact(s)\nSmall dots: scans • rings: detected contacts')
   if self.picking and i==self.owner.selected():
    p.setPen(QColor('#ffe887'));p.drawText(QRectF(i*pane_width+12,105,pane_width-24,45),'Pick '+['TOP LEFT','TOP RIGHT','BOTTOM RIGHT','BOTTOM LEFT'][len(self.corners)])
    for q in self.corners:p.drawEllipse(self.to_view(q,i),7,7)
   p.restore()
  p.setPen(QPen(QColor('#446078'),2));p.drawLine(QPointF(pane_width,0),QPointF(pane_width,self.height()));p.end()
 def mousePressEvent(self,e):
  if not self.picking:return
  self.corners.append(self.to_world(e.position()).tolist())
  if len(self.corners)==4:
   try:
    h=fit_homography(self.corners,[[0,0],[1,0],[1,1],[0,1]])
    proc=self.owner.processors[self.owner.selected()];proc.settings.update(roi=self.corners,matrix=h.tolist(),calibrated=False,verified=False);proc.matrix=h
    self.owner.message('Screen boundary updated. Now run finger calibration.');self.picking=False;self.corners=[]
   except Exception as exc:self.owner.message(str(exc));self.corners=[]
  self.update()
 def keyPressEvent(self,e):
  if e.key()==Qt.Key.Key_Escape:self.picking=False;self.corners=[];self.update()

class TouchCanvas(QWidget):
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
  else:
   if validation:
    # One unpredictable target in each of twelve screen regions.
    rng=np.random.default_rng();uv=[((col+rng.uniform(.2,.8))/4,(row+rng.uniform(.2,.8))/3) for row in range(3) for col in range(4)];rng.shuffle(uv)
   else:uv=[(.04,.04),(.96,.04),(.96,.96),(.04,.96)]
  return [np.array([l+x*(r-l),t+y*(b-t)]) for x,y in uv]
 def tick(self):
  if self.sensor is not None:self.calibration_tick()
  self.update()
 def calibration_tick(self):
  proc=self.owner.processors[self.sensor];now=time.monotonic()
  if now-proc.last_frame>.8:self.note='Waiting for fresh SDK scans…';self.samples=[];return
  blobs=proc.clusters
  if self.phase=='verify' and proc.matrix is not None:
   blobs=[blob for blob in blobs if np.isfinite(project(proc.matrix,[blob['world']])).all() and np.all(project(proc.matrix,[blob['world']])[0]>=0) and np.all(project(proc.matrix,[blob['world']])[0]<=1)]
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
   if self.phase=='verify' and not self.refine:
    uv=project(proc.matrix,[median])[0]
    error=float(np.linalg.norm((uv-self.targets[self.index])*[self.width(),self.height()]))
    tolerance=max(18.,min(self.width(),self.height())*.025)
    if not np.isfinite(error) or error>tolerance:
     self.samples=[];self.anchor=None;self.progress=0;self.note=f'Touch the highlighted target — detected contact is {error:.0f}px away';return
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
    self.phase='verify';self.world=[];self.targets=self.grid(True);self.index=0;self.note='Orientation detected. Touch each of the 12 highlighted test points' if not self.refine else 'Independent accuracy checks';return
   delta=project(proc.matrix,self.world)-self.targets
   errors=np.linalg.norm(delta*scale,axis=1);rms=float(np.sqrt(np.mean(errors**2)));maximum=float(errors.max());fraction=float(np.linalg.norm(delta,axis=1).max())
   passed=maximum<=self.owner.accuracy.value() if self.refine else maximum<=max(18.,min(self.width(),self.height())*.025)
   if not passed:raise ValueError((f'Precision check missed by {maximum:.1f}px.' if self.refine else f'Touch test missed by {maximum:.1f}px.')+' Check target captures and repeat. Previous calibration retained.')
   roi=project(np.linalg.inv(proc.matrix),[[0,0],[1,0],[1,1],[0,1]]).tolist()
   proc.settings.update(matrix=proc.matrix.tolist(),roi=roi,calibrated=True,verified=True,precision_verified=self.refine,calibration_method='9-point-refinement' if self.refine else 'four-corners-12-random-tests',fit_rms_px=self.pending_fit,validation_rms_px=rms,validation_max_px=maximum,center_error_fraction=fraction,validation_resolution=[self.width(),self.height()])
   self.committed=True;self.owner.save_profile(silent=True)
   detail=f'precision RMS {rms:.1f}px, max {maximum:.1f}px' if self.refine else f'12/12 targets passed, maximum error {maximum:.1f}px'
   self.owner.message(f'{proc.settings["name"]}: alignment saved — {detail}. Touch area ready. TUIO will be enabled.')
   self.close()
   QTimer.singleShot(0,lambda:self.owner.output.setChecked(True))
  except Exception as exc:self.owner.message(str(exc));self.close()
 def paintEvent(self,e):
  p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.fillRect(self.rect(),QColor('#061629'));p.setPen(QColor('#d8f5ff'));p.setFont(QFont('Segoe UI',19,QFont.Weight.Bold))
  if self.sensor is None:title='Live touch test — Esc to close'
  else:
   step=self.index+1 if self.phase=='fit' else (9 if self.refine else 4)+self.index+1
   title=f'{self.owner.processors[self.sensor].settings["name"]} • '+('Precision refinement' if self.refine else 'Corners → 12 touch tests')+f' • {step}/{14 if self.refine else 16}'
  p.drawText(QRectF(20,15,self.width()-40,50),Qt.AlignmentFlag.AlignCenter,title)
  if self.sensor is not None and self.phase=='fit' and not self.refine:
   p.setFont(QFont('Segoe UI',16));p.drawText(QRectF(20,75,self.width()-40,50),Qt.AlignmentFlag.AlignCenter,'Touch '+['TOP LEFT','TOP RIGHT','BOTTOM RIGHT','BOTTOM LEFT'][min(self.index,3)]+' corner target')
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

class Studio(QMainWindow):
 def __init__(self,profile_path=None):
  super().__init__()
  for name in ('segoeui.ttf','segoeuib.ttf'):
   path=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'/name
   if path.exists():QFontDatabase.addApplicationFont(str(path))
  QApplication.setFont(QFont('Segoe UI',10))
  self.path=Path(profile_path) if profile_path else ROOT/'lidar-profile.json';self.profile=read_profile(self.path)
  self.processors=[SensorProcessor(s) for s in self.profile['sensors']];self.workers={};self.statuses=['Not connected']*2;self.devices=[None,None];self.tracker=TouchTracker();self.touches={};self.canvas=None;self.loading=False;self.frame_times=[[],[]]
  self.sender=TuioOutput(self.profile['output_host'],self.profile['output_port'])
  for i,proc in enumerate(self.processors):
   background=self.path.parent/f'{self.path.stem}-background-{i}.npy'
   if background.exists() and proc.settings.get('background_revision')==2:
    try:
     values=np.load(background,allow_pickle=False)
     if values.shape==(1440,):proc.baseline=values
    except Exception:pass
  self.setWindowTitle('Dual Lidar Touch Studio — Demo SDK');self.resize(1540,950)
  root=QWidget();self.setCentralWidget(root);outer=QVBoxLayout(root);top=QHBoxLayout();title=QLabel('Dual Lidar Touch Studio');title.setStyleSheet('font-size:25px;font-weight:700');top.addWidget(title);top.addStretch()
  self.save=QPushButton('Save profile');self.save.clicked.connect(lambda:self.save_profile());top.addWidget(self.save)
  self.load=QPushButton('Load profile');self.load.clicked.connect(self.load_profile);top.addWidget(self.load);outer.addLayout(top)
  self.banner=QLabel('1 Connect SDK • 2 Record empty background • 3 Touch four corners + 12 test points • 4 Test • 5 Enable TUIO');self.banner.setWordWrap(True);outer.addWidget(self.banner)
  body=QHBoxLayout();outer.addLayout(body,1);tabs=QTabWidget();tabs.setMaximumWidth(450);tabs.setMinimumWidth(390);body.addWidget(tabs)
  connection=QWidget();a=QVBoxLayout(connection);tabs.addTab(connection,'Connect')
  self.ips=[]
  for i,proc in enumerate(self.processors):
   box=QGroupBox(f'Lidar {i+1} — '+proc.settings['name']);box.setStyleSheet('QGroupBox { color: '+['#38d5ff','#ff77c8'][i]+'; }');bl=QVBoxLayout(box);ip=QLineEdit(proc.settings['ip']);self.ips.append(ip);bl.addWidget(ip);label=QLabel('Not connected');label.setWordWrap(True);bl.addWidget(label);setattr(self,f'status_{i}',label);a.addWidget(box)
  self.connect_button=QPushButton('Connect both lidars');self.connect_button.clicked.connect(self.connect_sensors);a.addWidget(self.connect_button)
  stop=QPushButton('Stop scans');stop.clicked.connect(self.stop_sensors);a.addWidget(stop)
  a.addWidget(QLabel('Calibration display'));self.screens=QComboBox();self.screens.addItems([f'{i+1}: {s.name()} — {s.geometry().width()} × {s.geometry().height()}' for i,s in enumerate(QApplication.screens())]);self.screens.setCurrentIndex(min(self.profile.get('screen',0),self.screens.count()-1));a.addWidget(self.screens)
  self.width_mm=QSpinBox();self.width_mm.setRange(200,20000);self.width_mm.setValue(self.profile['width_mm']);self.width_mm.hide()
  self.height_mm=QSpinBox();self.height_mm.setRange(200,20000);self.height_mm.setValue(self.profile['height_mm']);self.height_mm.hide()

  note=QLabel('No guessed dimensions or screen boundary are required. This uses the SDK connection and corner calibration to automatically determine screen orientation. Mount the scan planes just in front of and parallel to the screen. Close FrameGrabber and other direct controllers first.');note.setWordWrap(True);a.addWidget(note);a.addStretch()
  tuning=QWidget();b=QVBoxLayout(tuning);tuning_scroll=QScrollArea();tuning_scroll.setWidgetResizable(True);tuning_scroll.setWidget(tuning);tabs.addTab(tuning_scroll,'Calibrate')
  self.selector=QComboBox();self.selector.addItems(['Bottom left','Bottom right']);b.addWidget(self.selector)
  self.coverage=QComboBox();self.coverage.addItems(['Whole screen','Left 70% (overlap)','Right 70% (overlap)']);b.addWidget(QLabel('Sensor coverage'));b.addWidget(self.coverage)
  self.yaw=QSpinBox();self.yaw.setRange(-180,180);b.addWidget(QLabel('Scan rotation (degrees)'));b.addWidget(self.yaw)
  self.threshold=QSpinBox();self.threshold.setRange(10,500);b.addWidget(QLabel('Foreground separation from background (mm)'));b.addWidget(self.threshold)
  self.blob=QSpinBox();self.blob.setRange(20,500);b.addWidget(QLabel('Maximum detected hand radius (mm)'));b.addWidget(self.blob)
  self.minimum=QSpinBox();self.minimum.setRange(1,30);b.addWidget(QLabel('Minimum rays per contact'));b.addWidget(self.minimum)
  self.learn_button=QPushButton('Record empty background (both, 2 seconds)');self.learn_button.clicked.connect(self.learn_empty);b.addWidget(self.learn_button)
  self.pick=QPushButton('Pick screen corners on selected scan');self.pick.clicked.connect(self.pick_corners);self.pick.hide()
  self.calibrate=QPushButton('Start guided calibration: corners + 12 tests');self.calibrate.clicked.connect(self.begin_calibration);b.addWidget(self.calibrate)
  self.refine_button=QPushButton('Optional: precision refinement (9 + 5)');self.refine_button.clicked.connect(self.begin_refinement);self.refine_button.hide()
  self.raw_label=QLabel('Raw hand detections: 0');self.raw_label.setWordWrap(True);b.addWidget(self.raw_label)
  self.calibration_label=QLabel();self.calibration_label.setWordWrap(True);b.addWidget(self.calibration_label)
  help=QLabel('Record the empty background, then start guided calibration for each sensor. Touch TL → TR → BR → BL: orientation and rotation are calculated automatically. Then touch 12 random targets within the screen. Lift between targets. After all pass, TUIO touch input is enabled for the exhibit.');help.setWordWrap(True);b.addWidget(help);b.addStretch()
  output=QWidget();c=QVBoxLayout(output);tabs.addTab(output,'Output')
  c.addWidget(QLabel('TUIO destination'));self.host=QLineEdit(self.profile['output_host']);c.addWidget(self.host);self.port=QSpinBox();self.port.setRange(1,65535);self.port.setValue(self.profile['output_port']);c.addWidget(self.port)
  self.merge=QSpinBox();self.merge.setRange(2,150);self.merge.setValue(self.profile.get('merge_px',24));c.addWidget(QLabel('Cross-sensor merge distance (screen pixels)'));c.addWidget(self.merge)
  self.smooth=QDoubleSpinBox();self.smooth.setRange(.1,1);self.smooth.setSingleStep(.05);self.smooth.setValue(self.profile.get('smoothing',.65));c.addWidget(QLabel('Responsiveness (1 = no smoothing)'));c.addWidget(self.smooth)
  self.accuracy=QSpinBox();self.accuracy.setRange(3,50);self.accuracy.setValue(self.profile.get('accuracy_px',8));c.addWidget(QLabel('Optional precision-check error limit (pixels)'));c.addWidget(self.accuracy)
  self.output=QCheckBox('Enable TUIO output');self.output.toggled.connect(self.toggle_output);c.addWidget(self.output)
  self.touch_label=QLabel('0 touches');c.addWidget(self.touch_label)
  test=QPushButton('Fullscreen touch test');test.clicked.connect(self.begin_test);c.addWidget(test)
  launch=QPushButton('Launch touchscreen exhibit');launch.clicked.connect(self.launch_exhibit);c.addWidget(launch)
  text=QLabel('Output uses one fused TUIO source so overlapping lidars do not double-click. Only aligned, checked and fresh sensors contribute. The touchscreen exhibit listens on 127.0.0.1:3333. This does not install a Windows touchscreen driver.');text.setWordWrap(True);c.addWidget(text);c.addStretch()
  area=QWidget();v=QVBoxLayout(area);controls=QHBoxLayout();controls.addWidget(QLabel('Scan view range (meters)'));self.zoom=QDoubleSpinBox();self.zoom.setRange(1,30);self.zoom.setValue(8);controls.addWidget(self.zoom)
  fit=QPushButton('Fit live scan');fit.clicked.connect(self.fit_view)
  controls.addWidget(fit);controls.addStretch();v.addLayout(controls);self.scanview=ScanView(self);v.addWidget(self.scanview,1);body.addWidget(area,1)
  self.message_label=QLabel('Ready. Stop FrameGrabber/RoboStudio before connecting so only one app controls the sensors.');self.message_label.setWordWrap(True);outer.addWidget(self.message_label)
  self.setStyleSheet('QWidget{background:#102237;color:#deeffa;font-family:Segoe UI;font-size:13px;} QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox{background:#1c354c;border:1px solid #385a73;padding:7px;border-radius:5px;} QPushButton{background:#176887;border:1px solid #3799ba;padding:11px;border-radius:6px;} QPushButton:hover{background:#2285a4;} QGroupBox{border:1px solid #35516b;border-radius:7px;margin-top:12px;padding-top:12px;} QTabBar::tab{padding:10px;}')
  self.selector.currentIndexChanged.connect(self.load_sensor_controls)
  for control in (self.yaw,self.threshold,self.blob,self.minimum):control.valueChanged.connect(self.change_sensor_controls)
  self.coverage.currentIndexChanged.connect(self.change_sensor_controls);self.zoom.valueChanged.connect(lambda:self.scanview.update())
  self.load_sensor_controls();self.timer=QTimer(self);self.timer.timeout.connect(self.tick);self.timer.start(33)
 def selected(self):return self.selector.currentIndex()
 def target_screen(self):return QApplication.screens()[self.screens.currentIndex()]
 def message(self,text):self.message_label.setText(text)
 def load_sensor_controls(self):
  self.loading=True;s=self.processors[self.selected()].settings
  self.yaw.setValue(s.get('yaw',0));self.threshold.setValue(s.get('foreground_mm',60));self.blob.setValue(s.get('max_radius_mm',160));self.minimum.setValue(s.get('min_points',3))
  self.coverage.setCurrentIndex(1 if s['coverage'][2]==.7 else 2 if s['coverage'][0]==.3 else 0);self.loading=False;self.scanview.update()
 def change_sensor_controls(self):
  if self.loading:return
  proc=self.processors[self.selected()];s=proc.settings
  new_coverage=[[0,0,1,1],[0,0,.7,1],[.3,0,1,1]][self.coverage.currentIndex()]
  changed_yaw=s.get('yaw',0)!=self.yaw.value() or s.get('coverage')!=new_coverage;s.update(yaw=self.yaw.value(),foreground_mm=self.threshold.value(),max_radius_mm=self.blob.value(),min_points=self.minimum.value(),coverage=[[0,0,1,1],[0,0,.7,1],[.3,0,1,1]][self.coverage.currentIndex()])
  if changed_yaw:s.update(calibrated=False,verified=False);self.output.setChecked(False)
 def fit_view(self):
  proc=self.processors[self.selected()]
  if len(proc.points):self.zoom.setValue(min(30,max(1,float(np.percentile(np.abs(proc.points),95))*2.4/1000)))
  self.scanview.update()
 def apply_layout(self):
  self.output.setChecked(False);w=self.width_mm.value();h=self.height_mm.value()
  for i,proc in enumerate(self.processors):
   corners=[[0,h],[w,h],[w,0],[0,0]] if i==0 else [[-w,h],[0,h],[0,0],[-w,0]]
   matrix=fit_homography(corners,[[0,0],[1,0],[1,1],[0,1]])
   proc.settings.update(roi=corners,matrix=matrix.tolist(),calibrated=False,verified=False);proc.matrix=matrix
  self.profile.update(width_mm=w,height_mm=h);self.message('Approximate bottom mount layout applied. Learn empty scene, then calibrate both sensors.');self.scanview.update()
 def connect_sensors(self):
  for i,proc in enumerate(self.processors):
   if i in self.workers and self.workers[i].isRunning():continue
   # Like the reference demo, reconnecting requires a fresh empty-scene capture.
   proc.baseline=None;proc.clusters=[];proc.settings['background_revision']=0
   ip=self.ips[i].text().strip()
   if ip!=proc.settings['ip']:proc.settings.update(ip=ip,calibrated=False,verified=False,serial='');proc.baseline=None
   worker=LidarWorker(i,ip,proc.settings.get('port',8089));worker.frame.connect(self.on_scan);worker.status.connect(self.on_status);worker.device.connect(self.on_device);self.workers[i]=worker;self.statuses[i]='Connecting…';worker.start()
  self.message('Connecting available sensors. Sensors already scanning are left running.')
 def stop_sensors(self):
  self.output.setChecked(False)
  for worker in self.workers.values():worker.stop()
  for worker in self.workers.values():worker.wait(6500)
  self.touches={};self.tracker=TouchTracker()
 def on_status(self,index,text):self.statuses[index]=text
 def on_device(self,index,device):
  self.devices[index]=device;proc=self.processors[index];old=proc.settings.get('serial')
  if old and old!=device['serial']:
   proc.settings.update(calibrated=False,verified=False);proc.baseline=None;self.message('Sensor serial changed: learn background and recalibrate before output.')
  proc.settings['serial']=device['serial']
 def on_scan(self,index,scan):
  self.processors[index].update(scan);now=time.monotonic();self.frame_times[index]=[t for t in self.frame_times[index] if now-t<2]+[now]
 def learn_empty(self):
  if not any(time.monotonic()-p.last_frame<.6 for p in self.processors):self.message('Connect the lidars and wait for live points first.');return
  self.output.setChecked(False)
  for proc in self.processors:
   if time.monotonic()-proc.last_frame<.6:proc.learn()
  self.message('Learning: keep the whole touch area clear until both backgrounds are ready.')
 def pick_corners(self):
  self.output.setChecked(False);self.scanview.picking=True;self.scanview.corners=[];self.scanview.setFocus();self.message('Click physical screen corners in this scan: TL, TR, BR, BL. Esc cancels.');self.scanview.update()
 def begin_refinement(self):
  self.begin_calibration(refine=True)
 def begin_calibration(self,checked=False,refine=False):
  proc=self.processors[self.selected()]
  if time.monotonic()-proc.last_frame>.6:self.message('Selected sensor is not delivering fresh scans. Connect it first.');return
  if proc.baseline is None or proc.learn_count:self.message('Learn an empty background before finger calibration.');return
  self.output.setChecked(False);self.canvas=TouchCanvas(self,self.selected(),refine=refine)
 def begin_test(self):self.output.setChecked(False);self.canvas=TouchCanvas(self)
 def usable(self,proc):
  s=proc.settings;resolution=s.get('validation_resolution',[]);g=self.target_screen().geometry()
  return s.get('enabled',True) and s.get('calibrated') and s.get('verified') and proc.baseline is not None and not proc.learn_count and time.monotonic()-proc.last_frame<.5 and resolution==[g.width(),g.height()]
 def toggle_output(self,enabled):
  if enabled:
   if not any(self.usable(p) for p in self.processors):self.output.setChecked(False);self.message('No ready sensor. Complete background, calibration and validation on the selected display.');return
   self.sender.host=self.host.text().strip();self.sender.port=self.port.value();self.message('TUIO enabled. Start the exhibit and test touches in its F2 diagnostics.')
  else:
   try:self.sender.send({})
   except OSError:pass
 def tick(self):
  now=time.monotonic();detections=[];g=self.target_screen().geometry()
  for i,proc in enumerate(self.processors):
   age=now-proc.last_frame
   if age>.5:proc.clusters=[]
   if proc.matrix is not None and age<.5 and not proc.learn_count:
    # Test shows calibrated positions even before validation succeeds; output still requires usable().
    if proc.settings.get('calibrated'):
     for blob in proc.clusters:
      uv=project(proc.matrix,[blob['world']])[0]
      l,t,r,b=proc.settings.get('coverage',[0,0,1,1])
      if np.isfinite(uv).all() and l<=uv[0]<=r and t<=uv[1]<=b and (not self.output.isChecked() or self.usable(proc)):detections.append((i,uv))
   frames=self.frame_times[i];fps=(len(frames)-1)/(frames[-1]-frames[0]) if len(frames)>1 and age<.6 else 0
   background=f'Recording {min(2,time.monotonic()-proc.learn_started):.1f}/2.0s • {len(proc.learning)} scans' if proc.learn_count else 'Background ready' if proc.baseline is not None else 'Record empty background'
   device=self.devices[i]
   identity=f' • S/N …{device["serial"][-8:]}' if device else ''
   label=getattr(self,f'status_{i}');label.setText(f'{self.statuses[i]} • {fps:.1f} scans/s{identity}\n{background} • {len(proc.clusters)} foreground clusters')
  self.touches=self.tracker.update(detections,(g.width(),g.height()),self.merge.value(),smoothing=self.smooth.value(),release_frames=5)
  ready=sum(bool(self.usable(p)) for p in self.processors)
  self.touch_label.setText(f'{len(self.touches)} fused touch(es) • {ready}/2 sensors aligned and ready')
  if self.output.isChecked() and self.canvas is None:
   try:self.sender.send(self.touches)
   except OSError as exc:self.output.setChecked(False);self.message('TUIO send error: '+str(exc))
  proc=self.processors[self.selected()];s=proc.settings
  self.raw_label.setText(f'Raw hand detections: {len(proc.clusters)} — available before calibration')
  self.calibration_label.setText(('Precision validated' if s.get('precision_verified') else 'Touch area verified — 12 targets passed' if s.get('verified') else 'Not calibrated — raw detections can still be captured')+(f'\nLast validation: RMS {s["validation_rms_px"]:.1f}px / maximum {s["validation_max_px"]:.1f}px' if 'validation_rms_px' in s else ''))
  self.scanview.update()
 def launch_exhibit(self):
  path=ROOT.parent/'TouchScreen'/'TouchScreen.exe'
  if path.exists():QProcess.startDetached(str(path),[],str(path.parent))
  else:self.message('Exhibit not found beside this folder. Launch TouchScreen.exe manually after enabling output.')
 def sync_profile(self):
  self.profile.update(screen=self.screens.currentIndex(),width_mm=self.width_mm.value(),height_mm=self.height_mm.value(),output_host=self.host.text().strip(),output_port=self.port.value(),merge_px=self.merge.value(),smoothing=self.smooth.value(),accuracy_px=self.accuracy.value(),sensors=[p.settings for p in self.processors])
 def save_profile(self,silent=False):
  self.sync_profile()
  try:
   self.path.parent.mkdir(parents=True,exist_ok=True)
   for i,proc in enumerate(self.processors):
    if proc.baseline is not None:np.save(self.path.parent/f'{self.path.stem}-background-{i}.npy',proc.baseline,allow_pickle=False)
   temp=self.path.with_suffix('.tmp');temp.write_text(json.dumps(self.profile,indent=2),encoding='utf-8');os.replace(temp,self.path)
   if not silent:self.message('Profile and background models saved to '+str(self.path))
  except Exception as exc:self.message('Save failed: '+str(exc))
 def load_profile(self):
  name,_=QFileDialog.getOpenFileName(self,'Load calibration profile',str(self.path),'JSON profile (*.json)')
  if not name:return
  try:
   profile=read_profile(name);self.stop_sensors();self.path=Path(name);self.profile=profile;self.processors=[SensorProcessor(s) for s in profile['sensors']]
   for i,proc in enumerate(self.processors):
    self.ips[i].setText(proc.settings['ip']);background=self.path.parent/f'{self.path.stem}-background-{i}.npy'
    if background.exists() and proc.settings.get('background_revision')==2:
     values=np.load(background,allow_pickle=False)
     if values.shape==(1440,):proc.baseline=values
   self.width_mm.setValue(profile['width_mm']);self.height_mm.setValue(profile['height_mm']);self.host.setText(profile['output_host']);self.port.setValue(profile['output_port']);self.screens.setCurrentIndex(min(profile.get('screen',0),self.screens.count()-1));self.merge.setValue(profile.get('merge_px',24));self.smooth.setValue(profile.get('smoothing',.65));self.accuracy.setValue(profile.get('accuracy_px',8));self.load_sensor_controls();self.message('Loaded profile. Reconnect sensors to verify serial numbers and live data.')
  except Exception as exc:self.message('Load failed: '+str(exc))
 def closeEvent(self,e):
  if self.canvas is not None:self.canvas.close()
  self.stop_sensors();self.save_profile(silent=True);self.sender.close();e.accept()

def main():
 app=QApplication(sys.argv)
 try:window=Studio(sys.argv[1] if len(sys.argv)>1 else None)
 except Exception as exc:QMessageBox.critical(None,'Lidar Touch Studio',str(exc));return 1
 window.show();return app.exec()
if __name__=='__main__':sys.exit(main())
