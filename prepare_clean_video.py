"""Prepare a clean-title copy; retain the original video untouched."""
import subprocess,cv2,numpy as np
from pathlib import Path
im=cv2.imread('video-preview.jpg');h=im[:153]
hsv=cv2.cvtColor(h,cv2.COLOR_BGR2HSV)
white=((hsv[:,:,1]<170)&(hsv[:,:,2]>140)).astype(np.uint8)*255
mask=np.zeros(h.shape[:2],np.uint8)
mask[62:95,480:1110]=white[62:95,480:1110]
mask[98:148,320:1280]=white[98:148,320:1280]
mask=cv2.dilate(mask,np.ones((9,9),np.uint8))
cv2.rectangle(mask,(581,21),(969,64),255,-1)
cv2.imwrite('assets/title-mask.png',mask)
soft=cv2.GaussianBlur(cv2.dilate(mask,np.ones((3,3),np.uint8)),(0,0),2).astype(np.float32)/255
soft=soft[:,:,None]
small_mask=cv2.resize(mask,(800,77),interpolation=cv2.INTER_NEAREST)
footer_masks=[]
for x0,x1 in ((0,370),(1230,1600)):
    crop=im[655:703,x0:x1]
    hsv_footer=cv2.cvtColor(crop,cv2.COLOR_BGR2HSV)
    footer_mask=((hsv_footer[:,:,1]<155)&(hsv_footer[:,:,2]>145)).astype(np.uint8)*255
    # Limit to the original baked footer's text lines.
    footer_mask[:7]=0;footer_mask[39:]=0
    footer_mask=cv2.dilate(footer_mask,np.ones((3,3),np.uint8))
    footer_masks.append((x0,x1,footer_mask))
button_masks=[]
for center in (214,508,800,1092,1384):
    left=center-140;right=center+140
    crop=im[484:535,left:right]
    hsv_button=cv2.cvtColor(crop,cv2.COLOR_BGR2HSV)
    text_mask=((hsv_button[:,:,1]<115)&(hsv_button[:,:,2]>165)).astype(np.uint8)*255
    text_mask=cv2.dilate(text_mask,np.ones((3,3),np.uint8))
    button_masks.append((left,right,text_mask))
def clean(image):
    top=image[:153]
    small=cv2.resize(top,(800,77),interpolation=cv2.INTER_AREA)
    fixed=cv2.inpaint(small,small_mask,4,cv2.INPAINT_TELEA)
    fixed=cv2.GaussianBlur(fixed,(0,0),.8)
    fixed=cv2.resize(fixed,(1600,153),interpolation=cv2.INTER_LINEAR)
    image[:153]=(fixed*soft+top*(1-soft)).astype(np.uint8)
    for x0,x1,footer_mask in footer_masks:
        crop=image[655:703,x0:x1]
        image[655:703,x0:x1]=cv2.inpaint(crop,footer_mask,3,cv2.INPAINT_TELEA)
    for left,right,text_mask in button_masks:
        image[484:535,left:right]=cv2.inpaint(image[484:535,left:right],text_mask,3,cv2.INPAINT_TELEA)
    return image
cv2.imwrite('assets/admin-background.jpg',clean(im.copy()))
cv2.imwrite('clean-video-preview.jpg',clean(im.copy()))
# Decode once at exhibit design resolution; h264 4:4:4 keeps the original odd height.
decoder=subprocess.Popen(['ffmpeg','-v','error','-i','Touch screen.mp4','-vf','scale=1600:703','-f','rawvideo','-pix_fmt','bgr24','-'],stdout=subprocess.PIPE)
encoder=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s','1600x703','-r','24','-i','-','-i','Touch screen.mp4','-map','0:v','-map','1:a?','-c:v','libx264','-preset','fast','-crf','17','-pix_fmt','yuv444p','-c:a','copy','-movflags','+faststart','Touch screen clean.mp4'],stdin=subprocess.PIPE)
size=1600*703*3;count=0
while True:
    raw=decoder.stdout.read(size)
    if not raw:break
    if len(raw)!=size:raise RuntimeError('Incomplete decoded frame')
    frame=np.frombuffer(raw,np.uint8).reshape(703,1600,3).copy()
    encoder.stdin.write(clean(frame).tobytes());count+=1
    if count%240==0:print(f'Cleaned {count}/1464 frames',flush=True)
encoder.stdin.close();assert decoder.wait()==0;assert encoder.wait()==0
print(f'Clean video ready: {count} frames',flush=True)
