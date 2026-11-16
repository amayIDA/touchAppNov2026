import math, wave, struct
from pathlib import Path
for name,frequencies in [('press',(740,1110)),('back',(660,440))]:
    rate=48000; duration=.15
    samples=[]
    for n in range(int(rate*duration)):
        t=n/rate
        env=(1-math.exp(-t/0.003))*math.exp(-t/0.033)*min(1,(duration-t)/.018)
        tone=sum(math.sin(2*math.pi*f*t)*a for f,a in zip(frequencies,(.65,.25)))
        samples.append(struct.pack('<h',int(32767*.42*env*tone)))
    with wave.open(str(Path('assets/audio')/(name+'.wav')),'wb') as wav:
        wav.setparams((1,2,rate,0,'NONE','not compressed')); wav.writeframes(b''.join(samples))
