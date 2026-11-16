import os,json,time
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
from app import QApplication,Exhibit,QTimer
app=QApplication([]);config=json.loads(Path('config.json').read_text(encoding='utf-8-sig'));config['tuio']['ports']=[]
w=Exhibit(config,True);w.resize(1600,696)
def capture():
 for i in range(5): w.open_topic(i);w.revealed[i]=time.monotonic()-3;w.icon_open[i]=1
 w.first_reveal=time.monotonic()-3;w.home_started=time.monotonic()-2;w.hover=-1;w.hover_amount=[0]*5
 w.grab().save('client-match-preview.png');w.close();app.quit()
QTimer.singleShot(2000,capture)
app.exec()

