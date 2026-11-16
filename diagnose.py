import pefile
from pathlib import Path
roots=[Path('dist/TouchScreen/_internal'),Path('dist/TouchScreen/_internal/PySide6'),Path('dist/TouchScreen/_internal/shiboken6'),Path('C:/Windows/System32')]
seen=set()
def scan(path):
    if path.name.lower() in seen:return
    seen.add(path.name.lower())
    try: pe=pefile.PE(str(path))
    except:return
    for imp in getattr(pe,'DIRECTORY_ENTRY_IMPORT',[]):
        name=imp.dll.decode(); found=next((r/name for r in roots if (r/name).exists()),None)
        if not found or name.lower().startswith(('api-','ext-')):continue
        dep=pefile.PE(str(found)); exports=getattr(dep,'DIRECTORY_ENTRY_EXPORT',None)
        names={s.name for s in exports.symbols} if exports else set()
        for s in imp.imports:
            if s.name and s.name not in names: print(path.name,'MISSING',name,s.name)
        if found.parent!=roots[-1]:scan(found)
scan(Path('dist/TouchScreen/_internal/PySide6/QtCore.pyd'))
