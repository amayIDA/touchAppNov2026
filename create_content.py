import json
from pathlib import Path
cards=[]
def f(label,text,size,rect,lang='en',color='#ffffff',bold=True):
    return dict(label=label,text=text,size=size,rect=rect,lang=lang,color=color,bold=bold)
def card(id,label,kind,rect,fields,group=None):
    c=dict(id=id,label=label,kind=kind,rect=rect,fields=fields)
    if group is not None:c['group']=group
    cards.append(c)
card('heading','Main heading','header',[320,15,960,133],[f('Arabic heading','سوق ينمو.. وحقوق تُصان',26,[12,0,936,37],'ar'),f('English heading','A Growing Labour Market, Protected Rights',27,[12,38,936,36]),f('Arabic subtitle','لكن مع كل هذا النمو وملايين العاملين.. كيف تضمن الإمارات حقوقهم واستقرارهم؟',17,[12,76,936,27],'ar',bold=False),f('English subtitle','But with this growth and millions of workers, how does the UAE safeguard their rights and ensure their stability?',17,[12,104,936,27],bold=False)])
cards[-1]['background']='#193f70';cards[-1]['radius']=22
names=[('Workforce Wellbeing System','منظومة جودة حياة القوى العاملة'),('Compliance and Inspection System','منظومة الامتثال والرقابة'),('Unemployment Insurance Scheme','منظومة التأمين ضد التعطل عن العمل'),('Workers Protection Programme','منظومة التأمين لحماية العمالة'),('Wage Protection System','منظومة حماية الأجور')]
centers=[214,508,800,1092,1384]
for i,(en,ar) in enumerate(names):
    card(f'button-{i}',en+' — button','button',[centers[i]-140,482,280,56],[f('Arabic label',ar,15,[7,3,266,25],'ar'),f('English label',en,14,[7,28,266,23])],i)
    cards[-1]['radius']=26
entries=[
 [('2+','million  مليون','عامل يقيمون في سكنات تستوفي معايير عالية','Paid to beneficiaries since the scheme’s launch'),('60+','','موقعاً على مستوى الدولة لتنفيذ فعاليات على مدار العام','Locations across the UAE hosting year-round events'),('800+','thousand  ألف','عامل متوسط المشاركين في الفعاليات','Average number of workers participating in these events')],
 [('600+','thousand  ألف','زيارة تفتيشية سنوياً','Inspection visits annually'),('66%','','زيادة في امتثال المنشآت لكل 1,000 زيارة تفتيشية','Increase in establishment compliance per 1,000 inspection visits')],
 [('620+','AED million  مليون درهم','صُرفت للمستفيدين منذ بدء المنظومة','Paid to beneficiaries since the scheme’s launch'),('93%','','من العمالة المستهدفة مشمولة بالمنظومة','Eligible workers covered by the scheme')],
 [('340+','AED million  مليون درهم','صُرفت للمستفيدين من المنظومة منذ بدء المنظومة','Paid to beneficiaries since the programme’s launch'),('99%','','من العمالة مشمولة بمنظومة التأمين لحماية العمالة','Workers covered by the programme')],
 [('37','AED billion  مليار درهم','تحويلات أجور شهرية','Digital transactions annually'),('99%','','من العمالة مشمولة بمنظومة حماية الأجور','Workers covered by the Wage Protection System')]]
for i,rows in enumerate(entries):
    for j,(number,unit,ar,en) in enumerate(rows):
        if i==0:
            rect=[centers[i]-133,171+j*91,266,85]
            fields=[f('Number',number,44,[155,6,105,48],color='#ff941e' if j==1 else '#ffffff'),f('Unit',unit,12,[150,55,110,23]),f('Arabic description',ar,12,[8,7,145,34],'ar'),f('English description',en,11,[8,42,145,36])]
        else:
            rect=[centers[i]-133,171+j*139,266,130]
            fields=[f('Number',number,62 if j==0 else 53,[8,0,250,66],color='#ff941e' if j==1 else '#ffffff'),f('Unit',unit,18,[7,65,252,23]),f('Arabic description',ar,13,[8,88 if unit else 66,250,23 if unit else 33],'ar'),f('English description',en,12,[8,110 if unit else 99,250,19 if unit else 28])]
        card(f'stat-{i}-{j}',names[i][0]+f' — card {j+1}','stat',rect,fields,i)
card('invitation','Standby invitation','invitation',[350,215,900,120],[f('Arabic invitation','المس علامة + أو اسم المنظومة لاستكشاف المزيد',25,[20,10,860,58],'ar'),f('English invitation','Tap + or a button to explore',23,[20,73,860,35])])
cards[-1]['background']='#092e51';cards[-1]['radius']=25
card('footer-en','English footer','footer',[8,658,360,45],[f('English footer','An integrated system that begins with wage protection and extends to compensation in the event of unemployment or the loss of entitlements',10,[5,3,350,39],bold=False)])
card('footer-ar','Arabic footer','footer',[1232,658,360,45],[f('Arabic footer','منظومة متكاملة تبدأ بحماية الأجور، وتمتد إلى التعويض عند التعطل أو فقدان المستحقات',11,[5,3,350,39],'ar',bold=False)])
for c in cards:
    if c['kind']=='footer': c['background']='#123d60';c['radius']=0
Path('content.json').write_text(json.dumps(dict(version=1,cards=cards),ensure_ascii=False,indent=2),encoding='utf-8')
