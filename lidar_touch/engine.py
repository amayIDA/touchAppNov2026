"""SLAMTEC standard-scan UDP transport and geometry/tracking primitives.
Command/packet layout follows SLAMTEC's public RPLIDAR protocol.
https://github.com/Slamtec/rplidar_sdk/blob/master/sdk/include/sl_lidar_cmd.h
"""
import socket,struct,time,threading,math,json,subprocess,sys,warnings
from pathlib import Path
import numpy as np
from pythonosc.osc_message_builder import OscMessageBuilder
from pythonosc.osc_bundle_builder import OscBundleBuilder,IMMEDIATELY
from PySide6.QtCore import QThread,Signal
BINS=1440

def project(matrix,points):
    p=np.asarray(points,dtype=float).reshape(-1,2)
    q=np.column_stack((p,np.ones(len(p))))@np.asarray(matrix,dtype=float).T
    with np.errstate(divide='ignore',invalid='ignore'): return q[:,:2]/q[:,2,None]

def fit_homography(world,screen):
    world=np.asarray(world,dtype=float);screen=np.asarray(screen,dtype=float)
    if len(world)<4 or len(world)!=len(screen):raise ValueError('At least four matching points are required')
    if not np.isfinite(world).all() or not np.isfinite(screen).all():raise ValueError('Nonfinite coordinates')
    def normalize(p):
        center=p.mean(axis=0);distance=np.linalg.norm(p-center,axis=1).mean()
        if distance<1e-8:raise ValueError('Calibration points overlap')
        scale=math.sqrt(2)/distance
        t=np.array([[scale,0,-scale*center[0]],[0,scale,-scale*center[1]],[0,0,1.]])
        return project(t,p),t
    a,ta=normalize(world);b,tb=normalize(screen);rows=[]
    for (x,y),(u,v) in zip(a,b):
        rows.extend([[-x,-y,-1,0,0,0,u*x,u*y,u],[0,0,0,-x,-y,-1,v*x,v*y,v]])
    rows=np.asarray(rows)
    if np.linalg.matrix_rank(rows)<8:raise ValueError('Calibration points are collinear or too close together')
    _,_,vh=np.linalg.svd(rows);h=np.linalg.inv(tb)@vh[-1].reshape(3,3)@ta
    if abs(h[2,2])<1e-12:raise ValueError('Degenerate calibration')
    return h/h[2,2]

def scan_nodes(buffer):
    """Recover standard 5-byte nodes; reject sync/check-bit/angle failures."""
    nodes=[];i=0
    while i+5<=len(buffer):
        b=buffer[i:i+5]
        angle=((b[1]>>1)|(b[2]<<7))/64
        if (b[0]&1)!=((b[0]>>1)&1) and b[1]&1 and angle<360:
            nodes.append((bool(b[0]&1),angle,int.from_bytes(b[3:5],'little')/4,b[0]>>2));i+=5
        else:i+=1
    return nodes,buffer[i:]

class LidarWorker(QThread):
    frame=Signal(int,object)
    status=Signal(int,str)
    device=Signal(int,object)
    def __init__(self,index,ip,port=8089):
        super().__init__();self.index=index;self.ip=ip;self.port=port;self.cancel=threading.Event();self.socket=None
    def stop(self):self.cancel.set()
    def query(self,command,size):
        self.socket.send(bytes([0xa5,command]));data=b'';end=time.monotonic()+2
        while not self.cancel.is_set() and time.monotonic()<end:
            try:data+=self.socket.recv(65535)
            except socket.timeout:continue
            at=data.find(b'\xa5\x5a')
            if at>=0 and len(data)>=at+7+size:return data[at+7:at+7+size]
        raise TimeoutError('No device response; check IP, power and close other lidar tools')
    def run(self):
        sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);self.socket=sock
        sock.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,4*1024*1024);sock.settimeout(.15)
        try:
            sock.connect((self.ip,self.port));sock.send(b'\xa5\x25')
            end=time.monotonic()+.35
            while time.monotonic()<end:
                try:sock.recv(65535)
                except socket.timeout:pass
            info=self.query(0x50,20);health=self.query(0x52,3)
            device={'model':info[0],'serial':info[4:20].hex().upper(),'firmware':f'{info[2]}.{info[1]:02d}','health':health[0]}
            self.device.emit(self.index,device)
            if health[0]==2:raise RuntimeError('Sensor reports an internal error; scanning not started')
            sock.send(b'\xa5\x20');header=b'';deadline=time.monotonic()+4
            while not self.cancel.is_set() and time.monotonic()<deadline:
                try:header+=sock.recv(65535)
                except socket.timeout:continue
                at=header.find(b'\xa5\x5a')
                if at>=0 and len(header)>=at+7:
                    if header[at+6]!=0x81:raise RuntimeError('This sensor did not accept standard-scan format')
                    remainder=header[at+7:];break
            else:raise TimeoutError('No scan descriptor received')
            self.status.emit(self.index,'Scanning');scan=[];last=time.monotonic();scan_started=last
            while not self.cancel.is_set():
                try:
                    data=remainder+sock.recv(65535);remainder=b''
                except socket.timeout:
                    if time.monotonic()-last>3 and time.monotonic()-scan_started>8:raise TimeoutError('Scan stream stopped; click Connect both lidars to retry this sensor')
                    continue
                last=time.monotonic()
                nodes,remainder=scan_nodes(data)
                for sync,angle,distance,quality in nodes:
                    if sync and len(scan)>100:
                        self.frame.emit(self.index,np.asarray(scan,dtype=np.float32));scan=[]
                    scan.append((angle,distance,quality))
                    if len(scan)>20000:raise RuntimeError('Missing revolution boundary; reconnect')
        except Exception as exc:self.status.emit(self.index,str(exc))
        finally:
            try:sock.send(b'\xa5\x25')
            except OSError:pass
            sock.close();self.socket=None
            if self.cancel.is_set():self.status.emit(self.index,'Stopped')

class SdkLidarWorker(LidarWorker):
    """The supplied demo's SLAMTEC SDK bridge, one independent process per lidar."""
    def __init__(self,index,ip,port=8089):
        super().__init__(index,ip,port);self.process=None
    def stop(self):
        self.cancel.set()
        if self.process is not None and self.process.poll() is None:
            try:self.process.stdin.write('stop\n');self.process.stdin.flush()
            except (OSError,ValueError):pass
            process=self.process
            def force_close():
                if process.poll() is None:
                    try:process.kill()
                    except OSError:pass
            timer=threading.Timer(3.5,force_close);timer.daemon=True;timer.start()
    def run(self):
        identity={};detail=[]
        try:
            # Read identity before handing the connection to the SDK process.
            sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);self.socket=sock;sock.settimeout(.15);sock.connect((self.ip,self.port))
            try:
                sock.send(b'\xa5\x25');end=time.monotonic()+.35
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
            cancelled=self.cancel.is_set()
            self.stop()
            if self.process is not None:
                try:self.process.wait(timeout=4)
                except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=2)
            if cancelled:self.status.emit(self.index,'Stopped')

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
                values=np.asarray(self.learning);counts=np.isfinite(values).sum(axis=0)
                ordered=np.sort(values,axis=0)
                self.baseline=ordered[np.minimum(counts//2,len(ordered)-1),np.arange(BINS)]
                self.learning=[];self.learn_count=0;self.settings['background_revision']=2
            self.clusters=[];return
        if self.baseline is None:self.clusters=[];return
        # Match the demo's +/- two angular bins, suppressing jitter on learned walls.
        nearest=np.minimum.reduce([np.roll(self.baseline,offset) for offset in range(-2,3)])
        fg=distance < nearest[bins]-self.settings.get('foreground_mm',60)
        pts=self.points[fg];angles=angle[fg];foreground_bins=bins[fg]
        # Deliberately do not crop through a guessed homography. Raw clusters are
        # required to bootstrap the first four-corner calibration.
        if not len(pts):self.clusters=[];return
        order=np.argsort(angles);pts=pts[order];angles=angles[order];foreground_bins=foreground_bins[order]
        gap=self.settings.get('cluster_gap_mm',100)
        breaks=(np.linalg.norm(np.diff(pts,axis=0),axis=1)>gap)|(np.diff(foreground_bins)>12)
        groups=np.split(pts,np.flatnonzero(breaks)+1)
        if len(groups)>1 and foreground_bins[0]+BINS-foreground_bins[-1]<12 and np.linalg.norm(groups[0][0]-groups[-1][-1])<gap:
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

class TouchTracker:
    def __init__(self):self.tracks={};self.next_id=1
    def update(self,detections,screen_size,merge_px=24,match_px=90,smoothing=.65,confirm_frames=3,release_frames=2):
        scale=np.asarray(screen_size,dtype=float)
        # Only fuse measurements from distinct sensors. Same-sensor nearby fingers remain distinct.
        fused=[]
        for sensor,uv in detections:
            best=None;bestdist=merge_px
            for j,item in enumerate(fused):
                dist=np.linalg.norm((np.mean(item['points'],axis=0)-uv)*scale)
                if sensor not in item['sensors'] and dist<bestdist:best=j;bestdist=dist
            if best is None:fused.append({'sensors':{sensor},'points':[np.asarray(uv)]})
            else:fused[best]['sensors'].add(sensor);fused[best]['points'].append(np.asarray(uv))
        points=[np.mean(item['points'],axis=0) for item in fused]
        candidates=sorted((np.linalg.norm((track['pos']-point)*scale),sid,j) for sid,track in self.tracks.items() for j,point in enumerate(points))
        assigned={};used=set()
        for distance,sid,j in candidates:
            if distance>match_px:break
            if sid not in assigned and j not in used:assigned[sid]=j;used.add(j)
        for sid in list(self.tracks):
            tr=self.tracks[sid]
            if sid in assigned:
                tr['pos']=tr['pos']*(1-smoothing)+points[assigned[sid]]*smoothing;tr['hits']+=1;tr['missed']=0
            else:
                tr['missed']+=1
                if tr['missed']>release_frames:del self.tracks[sid]
        for j,point in enumerate(points):
            if j not in used:
                self.tracks[self.next_id]={'pos':point,'hits':1,'missed':0};self.next_id+=1
        return {sid:tr['pos'].copy() for sid,tr in self.tracks.items() if tr['hits']>=confirm_frames}

class TuioOutput:
    def __init__(self,host='127.0.0.1',port=3333):
        self.socket=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);self.host=host;self.port=port;self.sequence=0
    def send(self,touches):
        bundle=OscBundleBuilder(IMMEDIATELY)
        def add(*args):
            msg=OscMessageBuilder(address='/tuio/2Dcur')
            for a in args:msg.add_arg(a)
            bundle.add_content(msg.build())
        add('source','DualLidarTouch@localhost');add('alive',*touches.keys())
        for sid,(x,y) in touches.items():add('set',int(sid),float(x),float(y),0.,0.,0.)
        add('fseq',self.sequence);self.sequence=(self.sequence+1)%2147483647
        self.socket.sendto(bundle.build().dgram,(self.host,self.port))
    def close(self):
        try:self.send({})
        finally:self.socket.close()
