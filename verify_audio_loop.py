import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import json
from pathlib import Path
from app import QApplication,Exhibit,QTimer
from PySide6.QtMultimedia import QMediaPlayer
app=QApplication([]); c=json.loads(Path('config.json').read_text(encoding='utf-8-sig')); c['tuio']['ports']=[3433]
w=Exhibit(c,True)
def seek():
    assert w.music.duration()>1000
    w.music.setPosition(w.music.duration()-300)
    QTimer.singleShot(1700,check)
def check():
    assert w.music.playbackState()==QMediaPlayer.PlaybackState.PlayingState
    assert w.music.position()<4000,(w.music.position(),w.music.duration())
    print('PASS: music wrapped to beginning and continued playing',flush=True)
    w.close();app.quit()
QTimer.singleShot(1500,seek)
app.exec()
