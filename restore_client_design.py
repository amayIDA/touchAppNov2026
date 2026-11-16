import pymupdf as f,json,copy
from pathlib import Path
out=Path('assets/reference');out.mkdir(exist_ok=True)
d=f.open('assets/source-artwork.pdf');p=d[0]
# Remove only the full-page blue gradient. Preserve original client graphics.
stream=b'\n'.join(d.xref_stream(x) for x in p.get_contents());end=stream.index(b'Q\nQ\n')+4
stream=stream[end:];xref=p.get_contents()[0];d.update_stream(xref,stream);p.set_contents(xref)
original=d.tobytes()
b=f.open(stream=original,filetype='pdf');bp=b[0]
bg=b'q\n/GS1 gs\n'+b'\n'.join(('/'+name+' Do').encode() for _,name,_,_ in p.get_xobjects())+b'\nQ\n'
b.update_stream(bp.get_contents()[0],bg)
import re
header=f.open(stream=original,filetype='pdf');hp=header[0]
header.update_stream(hp.get_contents()[0],re.sub(rb'BT.*?ET',b'',stream,flags=re.S))
scale=1600/4920.445
# The PDF is the production artwork; targets follow the client-supplied 1600 x 696 visual.
forms={name:(x,box) for x,name,_,box in p.get_xobjects()}
formnames=[['Fm10','Fm9','Fm8'],['Fm6','Fm7'],['Fm5','Fm4'],['Fm3','Fm1'],['Fm2','Fm0']]
centers=[210,505,798,1091,1384]
data=json.loads(Path('content.json').read_text(encoding='utf-8'))
old={c['id']:c for c in data['cards']}
# Adopt the client's wording and layout as a named baseline; keep the old file as backup.
for name in ('content.json','dist/TouchScreen/content.json'):
 path=Path(name)
 if path.exists():Path(name+'.before-client-match.json').write_bytes(path.read_bytes())

def export(name,rect,bgpage=bp):
 p.get_pixmap(clip=f.Rect(*rect),alpha=True).save(str(out/(name+'.png')))
 bgpage.get_pixmap(clip=f.Rect(*rect),alpha=True).save(str(out/(name+'-background.png')))

def field(label,text,size,rect,lang='en',weight='ExtraBold',color='#ffffff'):
 return dict(label=label,text=text,size=size,rect=rect,lang=lang,color=color,bold=weight!='Plain',weight=weight)

def attach(c,name):
 c['template']='assets/reference/'+name+'.png';c['template_background']='assets/reference/'+name+'-background.png'
 c['reference_fields']=copy.deepcopy(c['fields'])

for i,names in enumerate(formnames):
 for j,name in enumerate(names):
  _,box=forms[name];x0,y0,x1,y1=box;clip=[x0,2162.946-y1,x1,2162.946-y0]
  key=f'stat-{i}-{j}';export(key,clip)
  c=old[key]
  c['rect']=[centers[i]-132,[168,262,351][j] if i==0 else [168,309][j],264,[82,76,85][j] if i==0 else 127]
  prior=c['fields'];values={v['label']:v['text'] for v in prior}
  number=values['Number']
  if i>0 and j==1:number='%'+number.replace('%','')
  unit=values['Unit'].replace('AED ','')
  if i==0:
   if j==0:
    rects=[[145,0,119,66],[145,62,119,20],[10,9,135,31],[10,40,135,28]];size=70
   elif j==1:
    rects=[[157,9,107,62],[155,58,109,18],[8,7,146,32],[8,39,146,30]];size=52
   else:
    rects=[[143,4,121,60],[141,60,123,23],[10,14,133,32],[10,46,135,29]];size=52
  else:
   rects=[[12,0,242,66],[6,62,252,27],[7,88,250,21],[7,107,250,20]] if j==0 else [[40,2,184,62],[6,62,252,1],[8,62,248,36],[8,97,248,29]]
   size=72 if j==0 else 54
  c['fields']=[field('Number',number,size,rects[0],weight='Black'),field('Unit',unit,22 if i else 12,rects[1],weight='Black'),field('Arabic description',values['Arabic description'],12.4 if i else 10,rects[2],'ar'),field('English description',values['English description'],12.4 if i else 10,rects[3])]
  if i>0 and j==1:c['fields'][0]['color']='#ff8a00'
  if i==0 and j==1:c['fields'][0]['color']='#ff8a00'
  # Explicit line breaks from the client reference.
  if i==1 and j==1:
   c['fields'][2]['text']='زيادة في امتثال المنشآت\nلكل 1,000 زيارة تفتيشية'
   c['fields'][3]['text']='Increase in establishment compliance\nper 1,000 inspection visits'
  if i==3 and j==1:c['fields'][2]['text']='من العمالة مشمولة بمنظومة\nالتأمين لحماية العمالة'
  if i==4 and j==1:c['fields'][3]['text']='Workers covered by the Wage\nProtection System'
  attach(c,key)
# Original button labels and gradient silhouettes.
for i in range(5):
 key=f'button-{i}';name=f'Fm{15-i}';_,box=forms[name];x0,y0,x1,y1=box
 export(key,[x0,2162.946-y1,x1,2162.946-y0]);c=old[key];c['rect']=[centers[i]-132,483,264,49]
 c['fields'][0]['rect']=[5,2,254,25];c['fields'][0]['size']=15;c['fields'][0]['weight']='Black'
 c['fields'][1]['rect']=[5,25,254,23];c['fields'][1]['size']=14;c['fields'][1]['weight']='Black';attach(c,key)
# Render a full transparent header, placing it 6px higher to match the supplied image.
from PIL import Image
for page,name in [(p,'heading'),(hp,'heading-background')]:
 pix=page.get_pixmap(clip=f.Rect(0,0,4920.445,483),matrix=f.Matrix(scale,scale),alpha=True)
 image=Image.frombytes('RGBA',[pix.width,pix.height],pix.samples)
 canvas=Image.new('RGBA',(1600,151));canvas.paste(image,(0,-6));canvas.save(out/(name+'.png'))
c=old['heading'];c['rect']=[0,0,1600,151]
c['fields']=[field('Arabic heading','سوق ينمو.. وحقوق تُصان',24.9,[600,18,345,36],'ar','Black'),field('English heading','A Growing Labour Market, Protected Rights',29.19,[490,55,570,38],weight='Black'),field('Arabic subtitle','لكن مع كل هذا النمو وملايين العاملين.. كيف تضمن الإمارات حقوقهم واستقرارهم؟',18.39,[450,94,700,29],'ar','Plain'),field('English subtitle','But with this growth and millions of workers, how does the UAE safeguard their rights and ensure their stability?',18.39,[325,120,930,27],weight='Plain')];attach(c,'heading')
# Transparent footers remain unboxed, as requested.
for key,clip,target in [('footer-en',[76,2020,920,2125],[18,657,275,35]),('footer-ar',[4255,2020,4855,2125],[1382,657,195,35])]:
 export(key,clip);c=old[key];c['rect']=target;c['fields'][0]['rect']=[0,0,target[2],target[3]];c['fields'][0]['weight']='Plain';c['fields'][0]['size']=8.62 if key=='footer-en' else 9.92;attach(c,key)
for c in data['cards']:
 for v in c['fields']:v.setdefault('weight','ExtraBold' if v.get('bold') else 'Plain')
data['reference']='Client WhatsApp visual 2026-11-13 • original PDF artwork • Bahij fonts only'
Path('content.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print('Exported exact client card/header/button layers and editable baseline.')
