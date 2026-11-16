from pathlib import Path
p=Path('lidar_touch/engine.py');s=p.read_text(encoding='utf-8-sig').replace('import socket,struct,time,threading,math,json','import socket,struct,time,threading,math,json,subprocess,sys,warnings\nfrom pathlib import Path')
a=s.index('class SensorProcessor:');b=s.index('\nclass TouchTracker:',a)
s=s[:a]+'''class SdkLidarWorker(LidarWorker):
    """The supplied demo's SLAMTEC SDK bridge, one independent process per lidar."""
    def __init__(self,index,ip,port=8089):
        super().__init__(index,ip,port);self.process=None
    def stop(self):
        self.cancel.set()
        if self.process is not None and self.process.poll() is None:
            try:self.process.stdin.write('stop\\n');self.process.stdin.flush()
            except (OSError,ValueError):pass
    def run(self):
        identity={};detail=[]
        try:
            # Read identity before handing the connection to the SDK process.
            sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);self.socket=sock;sock.settimeout(.15);sock.connect((self.ip,self.port))
            try:
                sock.send(b'\\xa5\\x25');end=time.monotonic()+.35
                while time.monotonic()<end:
                    try:sock.recv(65535)
                    except socket.timeout:pass
                info=self.query(0x50,20);health=self.query(0x52,3)
                identity={'model':info[0],'serial':info[4:20].hex().upper(),'firmware':f'{info[2]}.{info[1]:02d}','health':health[0]}
                self.device.emit(self.index,identity)
                if health[0]==2:raise RuntimeError('Sensor health error')
            finally:sock.close();self.socket=None
            if self.cancel.is_set():return
            root=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))
            bridge=root/'bin'/'lidar-bridge.exe'
            if not bridge.exists():raise FileNotFoundError('Missing demo SDK bridge: '+str(bridge))
            self.status.emit(self.index,'Starting demo SDK scan mode…')
            self.process=subprocess.Popen([str(bridge),'udp',self.ip,str(self.port)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',bufsize=1,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            def stderr():
                for line in self.process.stderr:detail.append(line.strip());detail[:]=detail[-8:]
            threading.Thread(target=stderr,daemon=True).start()
            failed=False
            for line in self.process.stdout:
                if self.cancel.is_set():break
                try:message=json.loads(line)
                except (ValueError,TypeError):continue
                if message.get('type')=='error':
                    failed=True;self.status.emit(self.index,message.get('message','SDK error'));break
                if message.get('type')=='device':
                    identity.update({k:message[k] for k in ('model','firmware') if k in message});self.device.emit(self.index,identity)
                if message.get('type')=='scan':
                    points=np.asarray(message.get('points',[]),dtype=np.float32)
                    if points.ndim==2 and points.shape[1]==3 and len(points):
                        self.frame.emit(self.index,points);self.status.emit(self.index,'SDK scanning')
            if not self.cancel.is_set() and not failed:self.status.emit(self.index,'SDK stream stopped. '+(' '.join(detail)[-200:] or 'Click Connect to retry.'))
        except Exception as exc:self.status.emit(self.index,str(exc))
        finally:
            self.stop()
            if self.process is not None:
                try:self.process.wait(timeout=4)
                except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=2)
            if self.cancel.is_set():
                # Do not replace a useful SDK error message with a generic stopped label.
                pass

class SensorProcessor:
    """Demo-equivalent foreground detector. Calibration consumes unmapped blobs."""
    def __init__(self,settings):
        self.settings=settings;self.baseline=None;self.learning=[];self.learn_count=0;self.learn_started=0;self.learn_seconds=0
        self.last_scan=None;self.points=np.empty((0,2));self.clusters=[];self.last_frame=0;self.candidates=[]
        self.matrix=np.asarray(settings['matrix']) if settings.get('matrix') else None
    def learn(self,count=None):
        self.learning=[];self.learn_count=count if count is not None else 8;self.learn_seconds=0 if count is not None else 2
        self.learn_started=time.monotonic();self.baseline=None;self.clusters=[];self.candidates=[]
    def update(self,scan):
        self.last_frame=time.monotonic();self.last_scan=scan
        if scan.ndim!=2 or scan.shape[1]!=3:self.points=np.empty((0,2));self.clusters=[];return
        angle=np.mod(scan[:,0],360);distance=scan[:,1];quality=scan[:,2]
        valid=np.isfinite(scan).all(axis=1)&(distance>=self.settings.get('min_mm',50))&(distance<=self.settings.get('max_mm',20000))&(quality>=1)
        angle=angle[valid];distance=distance[valid]
        rad=np.deg2rad(angle)+math.radians(self.settings.get('yaw',0))
        self.points=np.column_stack((np.sin(rad)*distance,np.cos(rad)*distance))
        bins=np.minimum((angle*4).astype(int),BINS-1)
        ranges=np.full(BINS,np.inf);np.minimum.at(ranges,bins,distance)
        if self.learn_count:
            self.learning.append(ranges)
            if len(self.learning)>=self.learn_count and self.last_frame-self.learn_started>=self.learn_seconds:
                values=np.asarray(self.learning);values[~np.isfinite(values)]=np.nan
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore',RuntimeWarning);self.baseline=np.nanmedian(values,axis=0)
                self.baseline[~np.isfinite(self.baseline)]=np.inf
                self.learning=[];self.learn_count=0;self.settings['background_revision']=2
            self.clusters=[];return
        if self.baseline is None:self.clusters=[];return
        # Match the demo's +/- two angular bins, suppressing jitter on learned walls.
        nearest=np.minimum.reduce([np.roll(self.baseline,offset) for offset in range(-2,3)])
        fg=distance < nearest[bins]-self.settings.get('foreground_mm',60)
        pts=self.points[fg];angles=angle[fg]
        # Deliberately do not crop through a guessed homography. Raw clusters are
        # required to bootstrap the first four-corner calibration.
        if not len(pts):self.clusters=[];return
        order=np.argsort(angles);pts=pts[order];angles=angles[order]
        gap=self.settings.get('cluster_gap_mm',100)
        breaks=(np.linalg.norm(np.diff(pts,axis=0),axis=1)>gap)|(np.diff(angles)>3)
        groups=np.split(pts,np.flatnonzero(breaks)+1)
        if len(groups)>1 and angles[0]+360-angles[-1]<3 and np.linalg.norm(groups[0][0]-groups[-1][-1])<gap:
            groups=[np.vstack((groups[-1],groups[0]))]+groups[1:-1]
        result=[]
        for group in groups:
            if len(group)<self.settings.get('min_points',3):continue
            center=np.mean(group,axis=0);radius=np.linalg.norm(group-center,axis=1).max()
            if radius>=self.settings.get('max_radius_mm',160):continue
            result.append({'world':center,'size':float(radius*2),'rays':len(group)})
        # Rejoin split observations of the same hand, as in the reference demo.
        merge=self.settings.get('blob_merge_mm',80)
        for i in range(len(result)):
            if i>=len(result):break
            for j in range(len(result)-1,i,-1):
                if np.linalg.norm(result[i]['world']-result[j]['world'])<merge:
                    a=result[i];b=result.pop(j);n=a['rays']+b['rays'];a['world']=(a['world']*a['rays']+b['world']*b['rays'])/n;a['rays']=n
        self.clusters=result
''' +s[b:]
p.write_text(s,encoding='utf-8')
