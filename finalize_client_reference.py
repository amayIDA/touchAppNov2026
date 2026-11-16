import json,numpy as np
from pathlib import Path
from PIL import Image
# The background video already includes the translucent button silhouettes.
# Extract only the original text ink, avoiding a doubled blue background.
for i in range(5):
 root=Path(f'assets/reference/button-{i}')
 a=np.array(Image.open(str(root)+'.png').convert('RGBA')).astype(np.float64)/255
 b=np.array(Image.open(str(root)+'-background.png').convert('RGBA')).astype(np.float64)/255
 alpha=np.clip((a[:,:,3]-b[:,:,3])/(1-b[:,:,3]+1e-10),0,1)
 rgb=(a[:,:,:3]*a[:,:,3,None]-b[:,:,:3]*b[:,:,3,None]*(1-alpha[:,:,None]))/np.maximum(alpha[:,:,None],1e-9)
 result=np.dstack([np.clip(rgb,0,1),alpha]);Image.fromarray(np.round(result*255).astype(np.uint8)).save(str(root)+'.png')
 Image.new('RGBA',(a.shape[1],a.shape[0])).save(str(root)+'-background.png')
p=Path('content.json');d=json.loads(p.read_text(encoding='utf-8'))
rects={'stat-0-2':[78,350,264,85],'stat-1-1':[372,308,265,128],'stat-2-1':[666,308,264,127],'stat-3-1':[959,308,264,127],'stat-4-0':[1252,167,265,128],'stat-4-1':[1252,308,265,128],'button-1':[373,483,263,49],'button-2':[666,483,263,49],'button-4':[1253,483,263,49],'heading':[-3,1,1600,151]}
for c in d['cards']:
 if c['id'] in rects:c['rect']=rects[c['id']]
p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
# Preserve a copy of the client baseline for reliable restoration and comparison.
Path('assets/reference/client-content.json').write_bytes(p.read_bytes())
# Clean only the original button lettering; retain video scenery and button silhouettes.
p=Path('prepare_clean_video.py');s=p.read_text(encoding='utf-8')
s=s.replace('def clean(image):', '''button_masks=[]
for center in (214,508,800,1092,1384):
    left=center-140;right=center+140
    crop=im[484:535,left:right]
    hsv_button=cv2.cvtColor(crop,cv2.COLOR_BGR2HSV)
    text_mask=((hsv_button[:,:,1]<115)&(hsv_button[:,:,2]>165)).astype(np.uint8)*255
    text_mask=cv2.dilate(text_mask,np.ones((3,3),np.uint8))
    button_masks.append((left,right,text_mask))
def clean(image):''')
s=s.replace('    return image','''    for left,right,text_mask in button_masks:
        image[484:535,left:right]=cv2.inpaint(image[484:535,left:right],text_mask,3,cv2.INPAINT_TELEA)
    return image''')
p.write_text(s,encoding='utf-8')
