import os,json,time,tempfile,copy
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from app import Exhibit
from admin import Admin
from content_model import load_content,save_content
app=QApplication([])
folder=tempfile.TemporaryDirectory();path=Path(folder.name)/'content.json';save_content(path,load_content('content.json'))
a=Admin(path);a.show()
c=json.loads(Path('config.json').read_text(encoding='utf-8-sig'));c['tuio']['ports']=[]
w=Exhibit(c,True);w.content_path=path;w.content_stamp=path.stat().st_mtime_ns

def check():
    try:
        a.grab().save('admin-preview.png')
        w.clear_discoveries();w.grab().save('editable-standby.png')
        for i in range(5):w.open_topic(i);w.revealed[i]=time.monotonic()-3
        w.grab().save('editable-complete.png')
        index=next(i for i,c in enumerate(a.data['cards']) if c['id']=='stat-1-0')
        a.choose_card(index);a.editor.setPlainText('750+');a.size.setValue(50);a.save()
        w.last_content_check=0;w.tick()
        actual=next(c for c in w.editable['cards'] if c['id']=='stat-1-0')['fields'][0]
        assert actual['text']=='750+' and actual['size']==50,'Saved admin edit must hot-reload in exhibit'
        assert path.with_suffix('.json.bak').exists()
        a.choose_card(0);a.editor.setPlainText('اختبار العنوان');a.save();w.last_content_check=0;w.tick()
        assert w.editable['cards'][0]['fields'][0]['text']=='اختبار العنوان'
        a.select_heading();assert a.data['cards'][a.current]['kind']=='header'
        from PySide6.QtTest import QTest
        from PySide6.QtCore import QPoint,Qt
        r=a.preview.viewport()
        QTest.mouseClick(a.preview,Qt.MouseButton.LeftButton,pos=QPoint(round(r.x()+r.width()*.5),round(r.y()+r.height()*71/696)))
        assert a.field_select.currentIndex()==1,'Clicking English heading must select English field'
        from PySide6.QtGui import QImage,QPainter,QColor
        from content_model import draw_chrome
        image=QImage(1600,703,QImage.Format.Format_RGB32);image.fill(QColor('#b32e7a'))
        painter=QPainter(image);draw_chrome(painter,a.data,a.arabic);painter.end()
        assert image.pixelColor(20,20).name()=='#b32e7a','Header must not draw a background box'
        print('PASS: editor fields, Arabic persistence, size change, atomic save, backup and live exhibit reload',flush=True)
        a.dirty=False;a.close();w.close();app.exit(0)
    except Exception as exc:print(repr(exc),flush=True);a.dirty=False;a.close();w.close();app.exit(1)
QTimer.singleShot(3000,check)
raise SystemExit(app.exec())
