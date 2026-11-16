from pathlib import Path
p=Path('app.py'); s=p.read_text(encoding='utf-8-sig')
s=s.replace('self.topic = None; self.debug = False; self.hover = -1','self.debug = False; self.hover = -1\n        self.revealed = [None]*5\n        self.reset_started = None\n        self.first_reveal = None')
s=s.replace('        self.exiting_topic = None\n        self.exit_started = 0\n','')
s=s.replace('        self.frame = None; self.content_frame = None','        self.frame = None')
s=s.replace('        self.content, self.content_sink = self.player(self.foreground_frame)\n        self.content.errorOccurred.connect(lambda e,t: self.media_error(\'Content\', t))\n','')
s=s.replace('        self.content.mediaStatusChanged.connect(self.content_status)\n','')
a=s.index('    def foreground_frame('); b=s.index('    def viewport(',a)
s=s[:a]+'''    def media_error(self, which, text):
        self.errors.append(f'{which}: {text}'); logging.error('%s: %s', which, text)
        self.update()

'''+s[b:]
a=s.index('    def activate('); b=s.index('    def mousePressEvent(',a)
s=s[:a]+'''    def activate(self,p):
        self.last_action=time.monotonic()
        for i,cx in enumerate(CENTERS):
            if QRectF(cx-134,443,268,100).contains(p):
                if self.last_trigger[0] == i and time.monotonic()-self.last_trigger[1]<.45: return
                self.ripples.append((QPointF(p),time.monotonic()))
                self.last_trigger=(i,time.monotonic()); self.open_topic(i); return

    def open_topic(self,i):
        now=time.monotonic()
        if self.reset_started is not None: self.clear_discoveries()
        self.effects['press'].play()
        if self.revealed[i] is None:
            self.revealed[i]=now
            if self.first_reveal is None: self.first_reveal=now
        self.last_action=now
        logging.info('Revealed system %s',i)
        self.update()

    def clear_discoveries(self):
        self.revealed=[None]*5
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
        for i in range(5):
            target=1.0 if self.hover == i else 0.0
            self.hover_amount[i]+=(target-self.hover_amount[i])*.22
        self.ripples=[(pos,t) for pos,t in self.ripples if now-t < .7]
        if self.reset_started is not None and now-self.reset_started > .7:
            self.clear_discoveries()
        # A visitor holding a touch is still engaging with the exhibit.
        touching=any(self.touch_points.values())
        if touching: self.last_action=now
        if any(t is not None for t in self.revealed) and now-self.last_action>self.cfg.get('idle_return_seconds',45):
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

'''+s[b:]
s=s.replace('if self.hover>=0 or self.topic is not None else','if self.hover>=0 else')
s=s.replace('if self.topic is not None: self.home(feedback=True)','if any(t is not None for t in self.revealed): self.home(feedback=True)')
a=s.index('            reveal = ease((home_age-'); b=s.index('            hover =',a)
s=s[:a]+'''            revealed_at=self.revealed[i]
            reset_opacity=1-ease((now-self.reset_started)/.7) if self.reset_started is not None else 1
            if revealed_at is not None:
                self.draw_statistics(p,i,cx,now-revealed_at,reset_opacity)
'''+s[b:]
s=s.replace('            invitation = max(0,1-abs(phase-(3+i*.65))/.65)','            invitation = max(0,1-abs(phase-(3+i*.65))/.65) if revealed_at is None else 0')
s=s.replace("            p.drawPixmap(QRectF(cx-size/2,462-size/2,size,size),self.plus,QRectF(self.plus.rect()))",'''            p.drawPixmap(QRectF(cx-size/2,462-size/2,size,size),self.plus,QRectF(self.plus.rect()))
            if revealed_at is not None:
                progress=ease((now-revealed_at)/.4)*reset_opacity
                p.setPen(QPen(QColor(115,235,255,int(210*progress)),2.3))
                p.drawLine(QPointF(cx-22*progress,539),QPointF(cx+22*progress,539))''')
s=s.replace('            if 0 < sweep < 1:', '            if 0 < sweep < 1 and revealed_at is None:')
s=s.replace('        if self.topic is not None: self.draw_topic(p)\n        elif self.exiting_topic is not None: self.draw_topic(p,self.exiting_topic,True)','        self.draw_invitation(p,now)')
a=s.index('    def draw_topic('); b=s.index('    def closeEvent(',a)
s=s[:a]+'''    def draw_statistics(self,p,index,cx,age,opacity):
        pixmap=self.stats[index]
        # Preserve the supplied bilingual artwork while revealing each card in sequence.
        boundaries=[0, .35, .67, 1] if index == 0 else [0,.5,1]
        for row,(top,bottom) in enumerate(zip(boundaries,boundaries[1:])):
            progress=ease((age-row*.14)/.65)
            if progress<=0: continue
            source=QRectF(0,pixmap.height()*top,pixmap.width(),pixmap.height()*(bottom-top))
            target=QRectF(cx-133,171+269*top+18*(1-progress),266,269*(bottom-top))
            p.save(); p.setOpacity(progress*opacity)
            p.drawPixmap(target,pixmap,source)
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
        p.setPen(QPen(QColor(85,206,241,85),1))
        p.setBrush(QColor(5,30,62,190))
        p.drawRoundedRect(QRectF(460,215,680,112),25,25)
        self.text(p,QRectF(480,232,640,38),'المس علامة + أو اسم المنظومة لاستكشاف المزيد',22,bold=True,family=self.arabic_font)
        self.text(p,QRectF(480,275,640,30),'Tap a + or a system name to explore',19,color='#c9f1ff')
        p.restore()

'''+s[b:]
s=s.replace('        self.bg.stop(); self.content.stop()','        self.bg.stop()')
p.write_text(s,encoding='utf-8')
import json
c=Path('config.json'); config=json.loads(c.read_text(encoding='utf-8-sig')); config['idle_return_seconds']=45
c.write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
