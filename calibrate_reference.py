import cv2,json,numpy as np
ref=cv2.imread(r'C:\Users\ADMIN\Downloads\WhatsApp Image 2026-11-13 at 10.52.11 AM (1).jpeg')
d=json.load(open('content.json',encoding='utf-8'))
def ink(im):
 h=cv2.cvtColor(im[:,:,:3],cv2.COLOR_BGR2HSV)
 return (((h[:,:,1]<70)&(h[:,:,2]>210))|((h[:,:,0]>6)&(h[:,:,0]<30)&(h[:,:,1]>150)&(h[:,:,2]>170))).astype(np.float32)
ri=ink(ref)
for c in d['cards']:
 if c['kind'] not in ('stat','button'):continue
 t=cv2.imread(c['template'],cv2.IMREAD_UNCHANGED);mi=ink(t);mi[t[:,:,3]<220]=0
 x,y,w,h=map(int,c['rect']);crop=ri[max(0,y-14):y+h+14,max(0,x-14):x+w+14]
 best=(-1,None)
 for sc in np.linspace(.96,1.04,17):
  tw,th=round(w*sc),round(h*sc)
  temp=cv2.resize(mi,(tw,th),interpolation=cv2.INTER_AREA)
  result=cv2.matchTemplate(crop,temp,cv2.TM_CCOEFF_NORMED);_,score,_,loc=cv2.minMaxLoc(result)
  if score>best[0]:best=(score,(x-14+loc[0],y-14+loc[1],tw,th))
 print(c['id'],round(best[0],3),best[1])
