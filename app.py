"""Fullscreen labour-market exhibit. Python + Qt, offline, mouse/native touch/TUIO."""
import sys, json, math, time, logging, argparse
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, QUrl
from PySide6.QtGui import QPainter, QColor, QPixmap, QFont, QFontDatabase, QPen, QLinearGradient
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QVideoSink, QSoundEffect
from PySide6.QtNetwork import QUdpSocket, QHostAddress
from tuio import TuioState
from content_model import load_content,draw_card,draw_chrome,register_fonts

ROOT = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent
BUNDLE = Path(getattr(sys, '_MEIPASS', ROOT))
W, H = 1600, 696
CENTERS = [210, 505, 798, 1091, 1384]

def ease(value):
    value = max(0.0, min(1.0, value))
    return 1 - (1-value)**3

def resource(name):
    external = ROOT / name
    return external if external.exists() else BUNDLE / name

class Exhibit(QWidget):
    def __init__(self, config, windowed=False):
        super().__init__()
        self.cfg = config
        self.setWindowTitle('TouchScreen • Labour Market')
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents)
        self.setMouseTracking(True)
        self.resize(1600, 850)
        self.debug = False; self.hover = -1
        self.revealed = [None]*5
        self.collapsing = [None]*5
        self.icon_open = [0.0]*5
        self.reset_started = None
        self.first_reveal = None
        self.started = time.monotonic(); self.last_action = self.started
        self.home_started = self.started
        self.hover_amount = [0.0]*5
        self.ripples = []
        self.last_trigger = (-99, 0); self.touch_points = {}; self.errors = []
        self.frame = None
        self.stats = [QPixmap(str(resource(f'assets/stats-{i}.png'))) for i in range(5)]
        self.plus = QPixmap(str(resource('assets/plus.png')))
        self.buttons = [QPixmap(str(resource(f'assets/button-{i}.png'))) for i in range(5)]
        self.arabic_font=register_fonts(resource)
        self.content_path=resource('content.json')
        self.editable=load_content(self.content_path)
        self.content_stamp=self.content_path.stat().st_mtime_ns
        self.last_content_check=0
        audio_config = config.get('audio', {})
        self.music = QMediaPlayer(self)
        self.music_output = QAudioOutput(self)
        self.music_output.setVolume(max(0.0,min(1.0,audio_config.get('background_volume',.5))))
        self.music.setAudioOutput(self.music_output)
        self.music.setLoops(QMediaPlayer.Loops.Infinite)
        self.music.errorOccurred.connect(lambda e,t: self.media_error('Background music',t))
        self.music.setSource(QUrl.fromLocalFile(str(resource(audio_config.get('background_track','assets/audio/background.mp3')))))
        self.music.play()
        self.effects = {}
        for name in ('press','back'):
            effect = QSoundEffect(self)
            effect.setVolume(max(0.0,min(1.0,audio_config.get('effects_volume',.4))))
            effect.setSource(QUrl.fromLocalFile(str(resource(f'assets/audio/{name}.wav'))))
            self.effects[name] = effect
        self.bg, self.bg_sink = self.player(self.background_frame)
        self.bg.errorOccurred.connect(lambda e,t: self.media_error('Background', t))
        self.bg.setLoops(QMediaPlayer.Loops.Infinite)
        self.bg.setSource(QUrl.fromLocalFile(str(resource(config['background_video'])))); self.bg.play()
        self.tuio = TuioState(self.tuio_down, self.tuio_update)
        self.sockets = []
        tc = self.cfg['tuio']
        for port in tc['ports']:
            sock = QUdpSocket(self)
            if sock.bind(QHostAddress(tc['host']), port):
                sock.readyRead.connect(lambda s=sock: self.receive(s)); self.sockets.append(sock)
            else: self.errors.append(f'UDP {port}: {sock.errorString()}')
        self.timer = QTimer(self); self.timer.timeout.connect(self.tick); self.timer.start(33)
        screen = QApplication.screens()[min(config.get('screen',0), len(QApplication.screens())-1)]
        self.setGeometry(screen.geometry())
        if windowed or not config.get('fullscreen', True): self.resize(1440, 810); self.show()
        else: self.showFullScreen()

    def player(self, callback):
        player = QMediaPlayer(self); audio = QAudioOutput(self)
        audio.setMuted(self.cfg.get('mute', True)); player.setAudioOutput(audio)
        sink = QVideoSink(self); sink.videoFrameChanged.connect(lambda f: callback(f.toImage()))
        player.setVideoSink(sink)
        return player, sink

    def background_frame(self, image):
        if not image.isNull():
            if self.frame is None: self.home_started = time.monotonic()
            self.frame = image; self.update()

    def media_error(self, which, text):
        self.errors.append(f'{which}: {text}'); logging.error('%s: %s', which, text)
        self.update()

    def viewport(self):
        if self.cfg.get('fit') == 'stretch': return QRectF(0,0,self.width(),self.height())
        scale = min(self.width()/W, self.height()/H)
        return QRectF((self.width()-W*scale)/2,(self.height()-H*scale)/2,W*scale,H*scale)

    def local_point(self, x,y):
        r=self.viewport(); return QPointF((x-r.x())/r.width()*W,(y-r.y())/r.height()*H)

    def receive(self, sock):
        while sock.hasPendingDatagrams():
            data,host,port=sock.readDatagram(sock.pendingDatagramSize())
            self.tuio.feed(bytes(data),(host.toString(),port))

    def tuio_update(self, key, active):
        self.touch_points[key] = active

    def mapped_touch(self, source, x,y):
        tc=self.cfg['tuio']; transform=tc.get('sources',{}).get(source,{})
        if transform.get('swap_xy',tc.get('swap_xy')): x,y=y,x
        if transform.get('invert_x',tc.get('invert_x')): x=1-x
        if transform.get('invert_y',tc.get('invert_y')): y=1-y
        x=x*transform.get('scale_x',1)+transform.get('offset_x',0)
        y=y*transform.get('scale_y',1)+transform.get('offset_y',0)
        if tc.get('coordinate_space') == 'content': return QPointF(x*W,y*H)
        return self.local_point(x*self.width(), y*self.height())

    def tuio_down(self, source,sid,x,y):
        self.activate(self.mapped_touch(source,x,y))

    def activate(self,p):
        self.last_action=time.monotonic()
        for i,cx in enumerate(CENTERS):
            if QRectF(cx-134,443,268,100).contains(p):
                if self.last_trigger[0] == i and time.monotonic()-self.last_trigger[1]<.45: return
                self.ripples.append((QPointF(p),time.monotonic()))
                self.last_trigger=(i,time.monotonic()); self.open_topic(i); return

    def open_topic(self,i):
        now=time.monotonic()
        if self.reset_started is not None: self.clear_discoveries()
        if self.revealed[i] is None:
            self.effects['press'].play()
            self.collapsing[i]=None
            self.revealed[i]=now
            if self.first_reveal is None: self.first_reveal=now
        else:
            self.effects['back'].play()
            self.collapsing[i]=(now,now-self.revealed[i])
            self.revealed[i]=None
            if all(t is None for t in self.revealed):
                self.first_reveal=None
                self.home_started=now
        self.last_action=now
        logging.info('Revealed system %s',i)
        self.update()

    def clear_discoveries(self):
        self.revealed=[None]*5
        self.collapsing=[None]*5
        self.reset_started=None
        self.first_reveal=None
        self.home_started=time.monotonic()

    def home(self,feedback=False):
        if any(t is not None for t in self.revealed) and self.reset_started is None:
            if feedback: self.effects['back'].play()
            self.reset_started=time.monotonic()
        self.update()

    def tick(self):
        self.tuio.expire()
        now=time.monotonic()
        if now-self.last_content_check>.5:
            self.last_content_check=now
            try:
                stamp=self.content_path.stat().st_mtime_ns
                if stamp!=self.content_stamp:
                    updated=load_content(self.content_path)
                    self.editable=updated;self.content_stamp=stamp
                    logging.info('Applied admin content changes')
            except Exception as exc: logging.warning('Content reload: %s',exc)
        for i in range(5):
            target=1.0 if self.hover == i else 0.0
            self.hover_amount[i]+=(target-self.hover_amount[i])*.22
            icon_target=1.0 if self.revealed[i] is not None and self.reset_started is None else 0.0
            self.icon_open[i]+=(icon_target-self.icon_open[i])*.3
            if self.collapsing[i] is not None and now-self.collapsing[i][0]>.3:
                self.collapsing[i]=None
        self.ripples=[(pos,t) for pos,t in self.ripples if now-t < .7]
        if self.reset_started is not None and now-self.reset_started > .7:
            self.clear_discoveries()
        # A visitor holding a touch is still engaging with the exhibit.
        touching=any(self.touch_points.values())
        if touching: self.last_action=now
        if any(t is not None for t in self.revealed) and now-self.last_action>self.cfg.get('idle_return_seconds',20):
            self.home()
        self.update()

    def event(self,e):
        if e.type() in (e.Type.TouchBegin,e.Type.TouchUpdate):
            from PySide6.QtGui import QEventPoint
            for point in e.points():
                if point.state() == QEventPoint.State.Pressed:
                    self.activate(self.local_point(point.position().x(),point.position().y()))
            self.last_action=time.monotonic()
            e.accept(); return True
        if e.type() == e.Type.TouchEnd: e.accept(); return True
        return super().event(e)

    def mousePressEvent(self,e):
        if e.button()==Qt.MouseButton.LeftButton: self.activate(self.local_point(e.position().x(),e.position().y()))

    def mouseMoveEvent(self,e):
        p=self.local_point(e.position().x(),e.position().y())
        self.hover=next((i for i,c in enumerate(CENTERS) if QRectF(c-134,443,268,100).contains(p)),-1)
        self.setCursor(Qt.CursorShape.PointingHandCursor if self.hover>=0 else Qt.CursorShape.ArrowCursor)

    def leaveEvent(self,e):
        self.hover = -1
        super().leaveEvent(e)

    def keyPressEvent(self,e):
        key=e.key()
        if key==Qt.Key.Key_Escape:
            if any(t is not None for t in self.revealed): self.home(feedback=True)
            else: self.close()
        elif key==Qt.Key.Key_F11:
            self.showNormal() if self.isFullScreen() else self.showFullScreen()
        elif key==Qt.Key.Key_F2: self.debug=not self.debug
        elif key==Qt.Key.Key_Home: self.home(feedback=True)
        elif Qt.Key.Key_1<=key<=Qt.Key.Key_5: self.open_topic(key-Qt.Key.Key_1)

    def text(self,p,r,text,size=24,color='white',bold=False,family='Bahij TheSansArabic'):
        p.setPen(QColor(color)); p.setFont(QFont(family,size,QFont.Weight.Bold if bold else QFont.Weight.Normal))
        p.drawText(r,Qt.AlignmentFlag.AlignCenter|Qt.TextFlag.TextWordWrap,text)

    def paintEvent(self,e):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.fillRect(self.rect(),QColor('#050e22'))
        r=self.viewport(); p.setClipRect(r); p.translate(r.x(),r.y()); p.scale(r.width()/W,r.height()/H)
        if self.frame is not None: p.drawImage(QRectF(0,0,W,H),self.frame)
        else:
            p.fillRect(QRectF(0,0,W,H),QColor('#123a65'))
            self.text(p,QRectF(200,20,1200,120),'A Growing Labour Market, Protected Rights',32,bold=True)
        draw_chrome(p,self.editable,self.arabic_font,self.frame)
        now = time.monotonic()
        home_age = now-self.home_started
        for i,cx in enumerate(CENTERS):
            revealed_at=self.revealed[i]
            reset_opacity=1-ease((now-self.reset_started)/.7) if self.reset_started is not None else 1
            if revealed_at is not None:
                self.draw_statistics(p,i,cx,now-revealed_at,reset_opacity)
            elif self.collapsing[i] is not None:
                closed_at,age=self.collapsing[i]
                progress=ease((now-closed_at)/.3)
                p.save();p.translate(0,10*progress)
                self.draw_statistics(p,i,cx,age,(1-progress)*reset_opacity)
                p.restore()
            hover = self.hover_amount[i]
            # One slow travelling invitation, with a rest between cycles.
            phase = (now-self.home_started) % 14
            invitation = max(0,1-abs(phase-(3+i*.65))/.65) if revealed_at is None else 0
            energy = max(hover,invitation*.55)
            p.save()
            p.setOpacity(ease(home_age/.35))
            for spread,alpha in [(12,12),(7,22),(2,48)]:
                p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(42,201,247,int(alpha*energy)))
                p.drawRoundedRect(QRectF(cx-134-spread,483-spread,268+2*spread,51+2*spread),26+spread,26+spread)
            p.setPen(QPen(QColor(128,235,255,int(170*energy)),1.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(cx-134,483,268,51),26,26)
            pulse=1+.035*math.sin(now*1.7+i*.5)+.16*hover+.08*invitation
            size=35*pulse
            p.setPen(QPen(QColor(92,220,255,int(85*energy)),1.3))
            p.drawEllipse(QPointF(cx,462),23+5*energy,23+5*energy)
            # Morph the vertical stroke away to communicate the collapse action.
            p.save();p.translate(cx,462);p.scale(size/35,size/35)
            icon_fill=QLinearGradient(-17,-17,17,17)
            icon_fill.setColorAt(0,QColor('#075d91'));icon_fill.setColorAt(1,QColor('#22b9e8'))
            p.setPen(Qt.PenStyle.NoPen);p.setBrush(icon_fill)
            p.drawEllipse(QPointF(0,0),16.5,16.5)
            p.setPen(QPen(QColor('white'),3.5,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(-9,0),QPointF(9,0))
            vertical=9*(1-self.icon_open[i])
            if vertical>.15: p.drawLine(QPointF(0,-vertical),QPointF(0,vertical))
            p.restore()
            if revealed_at is not None:
                progress=ease((now-revealed_at)/.4)*reset_opacity
                p.setPen(QPen(QColor(115,235,255,int(210*progress)),2.3))
                p.drawLine(QPointF(cx-22*progress,539),QPointF(cx+22*progress,539))

            # Brief light sweep stays inside the pill; text remains stationary and legible.
            sweep = ((home_age-i*.65) % 14-3)/1.2
            if 0 < sweep < 1 and revealed_at is None:
                from PySide6.QtGui import QPainterPath
                path=QPainterPath(); path.addRoundedRect(QRectF(cx-134,483,268,51),26,26)
                p.save(); p.setClipPath(path,Qt.ClipOperation.IntersectClip)
                x=cx-180+360*sweep
                shine=QLinearGradient(x-40,0,x+40,0)
                shine.setColorAt(0,QColor(140,240,255,0)); shine.setColorAt(.5,QColor(160,242,255,45)); shine.setColorAt(1,QColor(140,240,255,0))
                p.fillRect(QRectF(x-40,483,80,51),shine); p.restore()
            p.restore()
        self.draw_invitation(p,now)
        for pos,t in self.ripples:
            progress = (now-t)/.7
            p.setPen(QPen(QColor(126,235,255,int(190*(1-progress))),2*(1-progress)+.5))
            p.setBrush(Qt.BrushStyle.NoBrush); p.drawEllipse(pos,12+90*ease(progress),12+90*ease(progress))
        if self.debug:
            p.fillRect(QRectF(10,10,540,115),QColor(0,0,0,210))
            active=sum(len(v) for v in self.touch_points.values())
            ports=', '.join(str(s.localPort()) for s in self.sockets)
            self.text(p,QRectF(20,18,520,95),f'TUIO UDP {ports}  |  {active} touches\nF2 diagnostics • F11 fullscreen • Esc back / exit\n'+('\n'.join(self.errors[-2:]) or 'Mouse + native touch + TUIO ready'),12)
            for key,points in self.touch_points.items():
                for sid,(x,y) in points.items():
                    pos=self.mapped_touch(key[1],x,y)
                    p.setPen(QPen(QColor('#ff9c25'),3)); p.setBrush(QColor(255,156,37,80)); p.drawEllipse(pos,14,14)
        elif self.errors:
            self.text(p,QRectF(400,665,800,30),'Playback or input issue — press F2 for details',12,color='#ffbd64')
        p.end()

    def draw_statistics(self,p,index,cx,age,opacity):
        cards=[c for c in self.editable['cards'] if c['kind']=='stat' and c['group']==index]
        for row,card in enumerate(cards):
            progress=ease((age-row*.14)/.65)
            if progress<=0: continue
            p.save();p.setOpacity(progress*opacity);p.translate(0,18*(1-progress))
            draw_card(p,card,self.arabic_font)
            p.restore()
        # A restrained opening glint acknowledges the new information, then settles.
        progress=(age-.25)/.8
        if 0<progress<1:
            p.save(); p.setOpacity(opacity)
            p.setPen(QPen(QColor(108,225,255,int(100*math.sin(progress*math.pi))),1.3))
            p.drawLine(QPointF(cx-100,171),QPointF(cx-100+200*ease(progress),171))
            p.restore()

    def draw_invitation(self,p,now):
        appeared=ease((now-self.home_started-.3)/.7)
        if self.first_reveal is not None:
            appeared*=1-ease((now-self.first_reveal)/.25)
        if appeared<=0: return
        p.save(); p.setOpacity(appeared)
        for card in self.editable['cards']:
            if card['kind']=='invitation': draw_card(p,card,self.arabic_font)
        p.restore()

    def closeEvent(self,e):
        self.music.stop()
        for effect in self.effects.values(): effect.stop()
        self.bg.stop()
        for s in self.sockets: s.close()
        super().closeEvent(e)

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--windowed',action='store_true'); args=parser.parse_args()
    logging.basicConfig(filename=str(ROOT/'touchscreen.log'),level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    app=QApplication(sys.argv)
    try: config=json.loads(resource('config.json').read_text(encoding='utf-8-sig'))
    except Exception as exc:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(None,'Configuration error',str(exc)); return 1
    window=Exhibit(config,args.windowed)
    return app.exec()

if __name__=='__main__': sys.exit(main())

