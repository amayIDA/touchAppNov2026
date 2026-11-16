from pathlib import Path
p=Path('lidar_touch/studio.py');s=p.read_text(encoding='utf-8');start=s.index(' def geometry_map(self):');end=s.index(' def mousePressEvent',start)
s=s[:start]+''' def geometry_map(self,sensor=None):
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
   p.drawText(QRectF(i*pane_width+12,42,pane_width-24,55),Qt.TextFlag.TextWordWrap,f'{state} • {count} detected contact(s)\\nSmall dots: scans • rings: detected contacts')
   if self.picking and i==self.owner.selected():
    p.setPen(QColor('#ffe887'));p.drawText(QRectF(i*pane_width+12,105,pane_width-24,45),'Pick '+['TOP LEFT','TOP RIGHT','BOTTOM RIGHT','BOTTOM LEFT'][len(self.corners)])
    for q in self.corners:p.drawEllipse(self.to_view(q,i),7,7)
   p.restore()
  p.setPen(QPen(QColor('#446078'),2));p.drawLine(QPointF(pane_width,0),QPointF(pane_width,self.height()));p.end()
''' +s[end:]
s=s.replace("box=QGroupBox(proc.settings['name']);bl=QVBoxLayout(box)","box=QGroupBox(f'Lidar {i+1} — '+proc.settings['name']);box.setStyleSheet('QGroupBox { color: '+['#38d5ff','#ff77c8'][i]+'; }');bl=QVBoxLayout(box)")
p.write_text(s,encoding='utf-8')
