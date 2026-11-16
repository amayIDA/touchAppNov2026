from pathlib import Path
p=Path('content_model.py');s=p.read_text(encoding='utf-8');s=s.replace('import json,copy,os','import json,copy,os,sys')
s=s.replace('QPen,QFontDatabase','QPen,QFontDatabase,QImage,QPainter')
a=s.index('def register_fonts(');b=s.index('\ndef load_content',a)
s=s[:a]+'''_asset=None
_image_cache={}
_card_cache={}

def register_fonts(asset):
    global _asset
    _asset=asset
    for name in ('assets/Arabic.ttf','assets/ArabicExtraBold.ttf','assets/ArabicRegular.ttf'):
        QFontDatabase.addApplicationFont(str(asset(name)))
    return 'Bahij TheSansArabic'

def artwork_image(name):
    if name not in _image_cache:
        path=_asset(name) if _asset else Path(__file__).parent/name
        _image_cache[name]=QImage(str(path))
    return _image_cache[name]

''' +s[b:]
a=s.index('def font_for(');b=s.index('\ndef fitted_font',a)
s=s[:a]+'''def font_for(field,arabic):
    font=QFont('Bahij TheSansArabic')
    weight=field.get('weight','Black' if field.get('bold',True) else 'Plain')
    font.setWeight({'Black':QFont.Weight.Black,'ExtraBold':QFont.Weight.ExtraBold,'Plain':QFont.Weight.Normal}[weight])
    font.setPixelSize(round(field['size']))
    return font

''' +s[b:]
s=s.replace("    p.save();r=QRectF(*card['rect']);p.translate(r.topLeft());local=QRectF(0,0,r.width(),r.height())", """    p.save();r=QRectF(*card['rect']);p.translate(r.topLeft());local=QRectF(0,0,r.width(),r.height())
    if card.get('template'):
        image=render_artwork_card(card,arabic)
        if not image.isNull():
            p.drawImage(local,image)
            p.restore();return""")
a=s.index('def draw_card(')
s=s[:a]+'''def render_artwork_card(card,arabic):
    key=json.dumps(card,sort_keys=True,ensure_ascii=False)
    if key in _card_cache:return _card_cache[key]
    original=artwork_image(card['template'])
    image=original.copy()
    if image.isNull():return image
    changes=[]
    baseline=card.get('reference_fields',[])
    for i,field in enumerate(card['fields']):
        prior=baseline[i] if i<len(baseline) else {}
        properties=('text','size','color','weight','rect')
        if any(field.get(k)!=prior.get(k) for k in properties):changes.append((field,prior))
    if changes:
        background=artwork_image(card['template_background'])
        painter=QPainter(image);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(image.width()/card['rect'][2],image.height()/card['rect'][3])
        local=QRectF(0,0,card['rect'][2],card['rect'][3])
        for field,prior in changes:
            painter.save()
            patch=QRectF(*prior.get('rect',field['rect']))
            painter.setClipRect(patch)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            painter.drawImage(local,background)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            painter.setFont(fitted_font(field,arabic));painter.setPen(QColor(field['color']))
            painter.drawText(QRectF(*field['rect']),Qt.AlignmentFlag.AlignCenter|Qt.TextFlag.TextWordWrap,field['text'])
            painter.restore()
        painter.end()
    if len(_card_cache)>128:_card_cache.clear()
    _card_cache[key]=image
    return image

''' +s[a:]
p.write_text(s,encoding='utf-8')
# Match the supplied client's artboard proportions.
for name in ('app.py','admin.py'):
 p=Path(name);s=p.read_text(encoding='utf-8-sig')
 if name=='app.py':
  s=s.replace('W, H = 1600, 703','W, H = 1600, 696').replace('CENTERS = [214, 508, 800, 1092, 1384]','CENTERS = [210, 505, 798, 1091, 1384]')
 else:
  s=s.replace('703','696').replace("font-family:Segoe UI","font-family:Bahij TheSansArabic").replace("else 'Segoe UI'","else 'Bahij TheSansArabic'")
  s=s.replace("self.bold=QCheckBox('Bold');pl.addWidget(self.bold)","self.bold=QCheckBox('Bold');self.bold.hide();self.weight=QComboBox();self.weight.addItems(['Black','ExtraBold','Plain']);pl.addWidget(QLabel('Bahij font weight'));pl.addWidget(self.weight)")
  s=s.replace('self.bold.toggled.connect(self.edit_field);','self.weight.currentTextChanged.connect(self.edit_field);')
  s=s.replace("self.bold.setChecked(f.get('bold',True))","self.bold.setChecked(f.get('bold',True));self.weight.setCurrentText(f.get('weight','ExtraBold'))")
  s=s.replace('bold=self.bold.isChecked(),color=',"bold=self.weight.currentText()!='Plain',weight=self.weight.currentText(),color=")
 p.write_text(s,encoding='utf-8')
# No exhibit fallback/debug text should use a different family.
p=Path('app.py');s=p.read_text(encoding='utf-8').replace("family='Segoe UI'","family='Bahij TheSansArabic'");p.write_text(s,encoding='utf-8')
for name in ('verify_app.py','verify_admin.py'):
 p=Path(name);s=p.read_text(encoding='utf-8-sig').replace('/703','/696');p.write_text(s,encoding='utf-8')
