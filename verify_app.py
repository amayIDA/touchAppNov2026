import os,time,json
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
from app import QApplication, Exhibit, QTimer, QPointF, CENTERS
from lidar_touch.engine import TuioOutput
from PySide6.QtMultimedia import QMediaPlayer,QSoundEffect
app=QApplication([])
config=json.loads(Path('config.json').read_text(encoding='utf-8-sig'))
w=Exhibit(config,True)
def check():
    try:
        assert w.frame is not None
        assert all(t is None for t in w.revealed), 'Standby must hide all statistics'
        assert w.music.playbackState()==QMediaPlayer.PlaybackState.PlayingState
        assert abs(w.music_output.volume()-.5)<.001
        assert all(s.status()==QSoundEffect.Status.Ready for s in w.effects.values())
        w.grab().save('standby-preview.png')
        for i,x in enumerate(CENTERS):
            for y in (462,510):
                w.clear_discoveries(); w.last_trigger.clear()
                w.activate(QPointF(x,y))
                assert [t is not None for t in w.revealed]==[j==i for j in range(5)]
        w.clear_discoveries();w.last_trigger.clear()
        r=w.viewport()
        def normal(x,y): return ((r.x()+r.width()*x/1600)/w.width(),(r.y()+r.height()*y/696)/w.height())
        x1,y1=normal(CENTERS[1],462);x2,y2=normal(CENTERS[3],510)
        sender=TuioOutput()
        # Interleave a second contact on the first column after the other column.
        sender.send({1:(x1,y1),2:(x2,y2),3:(x1,y1)})
        def after_udp():
            try:
                assert sum(map(len,w.touch_points.values()))==3, 'All three TUIO contacts must be tracked'
                assert [t is not None for t in w.revealed]==[False,True,False,True,False], 'Concurrent TUIO touches must reveal both columns'
                # Release cursors and let those two columns finish their entrances.
                sender.close()
                QTimer.singleShot(900,finish)
            except Exception as e: fail(e)
        QTimer.singleShot(150,after_udp)
    except Exception as e: fail(e)
def finish():
    try:
        w.grab().save('discovery-preview.png')
        prior=w.revealed[1];w.last_trigger.clear();w.activate(QPointF(CENTERS[1],462))
        assert w.revealed[1] is None and w.collapsing[1] is not None, 'Second tap must collapse its column'
        assert w.revealed[3] is not None, 'Collapsing one must preserve the others'
        w.last_trigger.clear();w.activate(QPointF(CENTERS[1],510))
        assert w.revealed[1] is not None and w.collapsing[1] is None, 'Label must reopen a collapsed column'
        for _ in range(30): w.tick()
        assert w.icon_open[1]>.99, 'Open icon must become minus'
        for i in range(5):
            if w.revealed[i] is None: w.open_topic(i)
        for i in range(5): w.revealed[i]=time.monotonic()-3
        w.ripples=[];w.grab().save('complete-preview.png')
        w.touch_points={};w.last_action=time.monotonic()-21;w.tick()
        assert w.reset_started is not None,'Idle must initiate reset'
        w.reset_started=time.monotonic()-.8;w.tick()
        assert all(t is None for t in w.revealed)
        # A new touch during the reset begins a clean discovery.
        w.open_topic(0);w.home();w.open_topic(4)
        assert [t is not None for t in w.revealed]==[False,False,False,False,True]
        print('PASS: hidden standby; 10 hit targets; independent concurrent UDP reveals; independent collapse/reopen; minus indicator; 20s idle reset; reset interruption; music at 50%; effects loaded',flush=True)
        w.close();app.exit(0)
    except Exception as e: fail(e)
def fail(error):
    print(repr(error),flush=True);w.close();app.exit(1)
QTimer.singleShot(3000,check)
raise SystemExit(app.exec())
