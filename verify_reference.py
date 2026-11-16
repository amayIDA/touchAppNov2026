import os,copy,json
os.environ['QT_QPA_PLATFORM']='offscreen'
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontInfo
from content_model import load_content,register_fonts,render_artwork_card,font_for
from pathlib import Path
from PIL import Image,ImageChops
app=QApplication([]);family=register_fonts(lambda n:Path(n));data=load_content('content.json')
for card in data['cards']:
 for field in card['fields']:
  assert QFontInfo(font_for(field,family)).family()=='Bahij TheSansArabic'
 if card.get('template'):
  image=render_artwork_card(card,family)
  from PySide6.QtGui import QImage
  original=QImage(card['template'])
  assert image==original,'Unchanged client artwork must be pixel-identical to its exported layer'
card=copy.deepcopy(next(c for c in data['cards'] if c['id']=='stat-2-0'))
render_artwork_card(card,family).save('reference-original-card.png')
card['fields'][0]['text']='750';render_artwork_card(card,family).save('reference-edited-card.png')
a=Image.open('reference-original-card.png');b=Image.open('reference-edited-card.png')
diff=ImageChops.difference(a,b).getbbox();assert diff is not None
r=card['fields'][0].get('erase_rect',card['fields'][0]['rect']);sx=a.width/card['rect'][2];sy=a.height/card['rect'][3]
assert diff[0]>=int(r[0]*sx)-2 and diff[2]<=int((r[0]+r[2])*sx)+2
assert diff[1]>=int(r[1]*sy)-2 and diff[3]<=int((r[1]+r[3])*sy)+2
print('PASS: Bahij fonts only; unchanged client layers pixel-identical; numeric edits preserve all artwork outside selected field')

