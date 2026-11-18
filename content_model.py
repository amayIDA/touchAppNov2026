"""Shared editable content, validation and drawing for exhibit and admin."""
import json,copy,os,sys
from pathlib import Path
from PySide6.QtCore import QRectF,Qt,QPointF
from PySide6.QtGui import QColor,QFont,QFontMetricsF,QLinearGradient,QPen,QFontDatabase,QImage,QPainter,QTextLayout

_asset=None
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


def load_content(path):
    data=json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if data.get('version')!=1 or not isinstance(data.get('cards'),list): raise ValueError('Unsupported content file')
    ids=set()
    for card in data['cards']:
        if card['id'] in ids: raise ValueError('Duplicate card ID')
        ids.add(card['id'])
        if len(card['rect'])!=4 or not all(isinstance(v,(float,int)) for v in card['rect']): raise ValueError('Invalid card bounds')
        for field in card['fields']:
            if not isinstance(field['text'],str) or len(field['text'])>2000: raise ValueError('Text must be at most 2000 characters')
            if not 6<=field['size']<=120: raise ValueError('Font size must be between 6 and 120')
            if not QColor(field['color']).isValid(): raise ValueError('Invalid text color')
    return data

def save_content(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    load_content(temp)
    os.replace(temp,path)

def font_for(field,arabic):
    font=QFont('Bahij TheSansArabic')
    weight=field.get('weight','Black' if field.get('bold',True) else 'Plain')
    font.setWeight({'Black':QFont.Weight.Black,'ExtraBold':QFont.Weight.ExtraBold,'Plain':QFont.Weight.Normal}[weight])
    font.setStyleName(weight)
    font.setPixelSize(round(field['size']))
    return font


def fitted_font(field,arabic):
    font=font_for(field,arabic);r=QRectF(*field['rect'])
    for size in range(round(field['size']),5,-1):
        font.setPixelSize(size)
        lines=text_lines(field['text'],font,r.width())
        metrics=QFontMetricsF(font)
        boxes=[metrics.tightBoundingRect(line) for line in lines]
        height=sum(box.height() for box in boxes)+max(0,len(boxes)-1)*size*.16
        if height<=r.height()+.5 and all(box.width()<=r.width()+.5 for box in boxes): return font
    return font

def text_lines(text,font,width):
    lines=[]
    for paragraph in text.split('\n'):
        if not paragraph:lines.append(' ');continue
        layout=QTextLayout(paragraph,font);layout.beginLayout()
        while True:
            line=layout.createLine()
            if not line.isValid():break
            line.setLineWidth(width)
            lines.append(paragraph[line.textStart():line.textStart()+line.textLength()])
        layout.endLayout()
    return lines

def draw_field(p,field,arabic):
    rect=QRectF(*field['rect']);font=fitted_font(field,arabic)
    p.setFont(font);p.setPen(QColor(field['color']))
    lines=text_lines(field['text'],font,rect.width());metrics=QFontMetricsF(font)
    boxes=[metrics.tightBoundingRect(line) for line in lines]
    gap=font.pixelSize()*.16
    total=sum(box.height() for box in boxes)+max(0,len(boxes)-1)*gap
    y=rect.center().y()-total/2
    for line,box in zip(lines,boxes):
        p.drawText(QPointF(rect.center().x()-box.center().x(),y-box.top()),line)
        y+=box.height()+gap

def render_artwork_card(card,arabic):
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
            patch=QRectF(*prior.get('erase_rect',prior.get('rect',field['rect'])))
            painter.setClipRect(patch)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            painter.drawImage(local,background)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            draw_field(painter,field,arabic)
            painter.restore()
        # Currency labels sit close to the curved leading numeral in the original.
        # Preserve that original ink when a numeric replacement clears its edge.
        for i,field in enumerate(card['fields']):
            if field.get('label')=='Currency label' and i<len(baseline) and field==baseline[i]:
                painter.save();painter.setClipRect(QRectF(*field['rect']))
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
                painter.drawImage(local,original);painter.restore()
        painter.end()
    if len(_card_cache)>128:_card_cache.clear()
    _card_cache[key]=image
    return image

def draw_card(p,card,arabic,selected=False):
    p.save();r=QRectF(*card['rect']);p.translate(r.topLeft());local=QRectF(0,0,r.width(),r.height())
    if card.get('template'):
        image=render_artwork_card(card,arabic)
        if not image.isNull():
            p.drawImage(local,image)
            p.restore();return
    if card['kind'] not in ('header','footer','invitation'):
        gradient=QLinearGradient(0,0,r.width(),r.height())
        gradient.setColorAt(0,QColor(card.get('background','#0b4d79')));gradient.setColorAt(1,QColor('#167fa4'))
        p.setBrush(gradient);p.setPen(QPen(QColor('#78e4ff'),2) if selected else Qt.PenStyle.NoPen)
        p.drawRoundedRect(local,card.get('radius',18),card.get('radius',18))
    for field in card['fields']:
        p.save();rect=QRectF(*field['rect']);p.setClipRect(rect,Qt.ClipOperation.IntersectClip)
        draw_field(p,field,arabic);p.restore()
    p.restore()

def draw_chrome(p,data,arabic,frame=None):
    # The cleaned video supplies the entire sky. Heading text is transparent.
    for card in data['cards']:
        if card['kind'] in ('header','button','footer'): draw_card(p,card,arabic)
