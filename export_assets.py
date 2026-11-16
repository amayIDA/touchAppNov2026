import pymupdf as f
from pathlib import Path
p=Path('assets')
d=f.open(r'C:\Users\ADMIN\Downloads\Touch screen\buttons.pdf')
page=d[0]
x=page.get_contents()[0]
s=d.xref_stream(x)
end=s.index(b'Q\nQ\n')+4
d.update_stream(x,s[end:])
page.get_pixmap(matrix=f.Matrix(.4,.4),alpha=True).save('assets/overlay-preview.png')
for i,(a,b) in enumerate([(260,1075),(1160,1975),(2055,2870),(2950,3765),(3845,4660)]):
    page.get_pixmap(clip=f.Rect(a,525,b,1352),alpha=True).save(f'assets/stats-{i}.png')
    page.get_pixmap(clip=f.Rect(a,1490,b,1645),alpha=True).save(f'assets/button-{i}.png')
page.get_pixmap(clip=f.Rect(614,1370,722,1475),alpha=True).save('assets/plus.png')
import shutil
shutil.copy(r'C:\Users\ADMIN\Downloads\Touch screen\buttons.pdf','assets/source-artwork.pdf')
shutil.copy(r'C:\Users\ADMIN\Downloads\Touch screen\buttons_Folder\Fonts\Bahij_TheSansArabic-Black.ttf','assets/Arabic.ttf')
