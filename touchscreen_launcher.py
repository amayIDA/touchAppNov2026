"""One-click Windows dependency bootstrapper; keep beside app.py."""
import argparse
import ctypes
import hashlib
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request

ROOT = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
PYTHON_URL = 'https://www.python.org/ftp/python/3.14.7/python-3.14.7-amd64.exe'
PYTHON_SHA256 = '9d9eb2709ef81bf5cd30db3c2096bdbc4ea10087c22e62f27d356b36f6ae9649'
PROBE = "import sys,struct,json;print(json.dumps({'exe':sys.executable,'version':list(sys.version_info[:2]),'bits':struct.calcsize('P')*8}))"
CHECK = """import importlib.metadata as m
from PySide6 import QtCore,QtGui,QtWidgets,QtMultimedia,QtNetwork
import pythonosc,numpy
assert m.version('PySide6')=='6.12.0'
assert m.version('python-osc')=='1.10.2'
assert m.version('numpy')=='2.5.3'
print('Runtime dependencies ready')
"""


def child_env():
    env = os.environ.copy()
    for key in ('PYTHONHOME','PYTHONPATH','QT_PLUGIN_PATH','QT_QPA_PLATFORM_PLUGIN_PATH'):
        env.pop(key, None)
    # A PyInstaller parent must not pass its own DLLs to a normal Python child.
    bundle = str(getattr(sys, '_MEIPASS', ''))
    if bundle:
        env['PATH'] = os.pathsep.join(p for p in env.get('PATH','').split(os.pathsep) if not p.casefold().startswith(bundle.casefold()))
    env['PYTHONUTF8'] = '1'
    return env


def run(args, timeout=60):
    result = subprocess.run([str(a) for a in args], cwd=ROOT, env=child_env(), capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.stdout.strip(): logging.info(result.stdout.strip())
    if result.stderr.strip(): logging.info(result.stderr.strip())
    return result


def valid_python(command):
    try:
        result = run([*command,'-c',PROBE], 15)
        data = json.loads(result.stdout.strip())
        return Path(data['exe']) if result.returncode == 0 and data['bits'] == 64 and [3,11] <= data['version'] <= [3,14] else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def find_python():
    local = Path(os.environ.get('LOCALAPPDATA',Path.home()/'AppData/Local'))
    candidates = []
    if not getattr(sys,'frozen',False): candidates.append([sys.executable])
    candidates.extend([[str(ROOT/'.touchscreen-env/Scripts/python.exe')], [str(ROOT/'.venv/Scripts/python.exe')]])
    for command in ('python','python3'):
        path = shutil.which(command)
        if path and 'windowsapps' not in path.lower(): candidates.append([path])
    for path in [*local.glob('Python/pythoncore-3.1*-64/python.exe'), *local.glob('Programs/Python/Python31*/python.exe'), local/'TouchScreen/Python314/python.exe']:
        candidates.append([str(path)])
    if shutil.which('py'): candidates.extend([['py',f'-3.{minor}'] for minor in (14,13,12,11)])
    for command in candidates:
        executable = valid_python(command)
        if executable: return executable
    return None


def install_python():
    cache = Path(os.environ.get('LOCALAPPDATA',Path.home()/'AppData/Local'))/'TouchScreen'
    cache.mkdir(parents=True,exist_ok=True)
    installer = cache/'python-3.14.7-amd64.exe'
    logging.info('Downloading Python from python.org (about 32 MB)...')
    with urllib.request.urlopen(PYTHON_URL, timeout=60) as response, installer.open('wb') as output:
        shutil.copyfileobj(response,output)
    if hashlib.sha256(installer.read_bytes()).hexdigest() != PYTHON_SHA256:
        raise RuntimeError('Python download checksum did not match. Please retry.')
    target = cache/'Python314'
    logging.info('Installing Python for your user account. No PATH changes...')
    result = run([installer,'/quiet','InstallAllUsers=0',f'TargetDir={target}','Include_pip=1','Include_test=0','Include_launcher=0','PrependPath=0','Shortcuts=0'],600)
    executable = valid_python([str(target/'python.exe')])
    if result.returncode not in (0,3010) or not executable:
        raise RuntimeError(f'Python installation failed ({result.returncode}). See touchscreen-launcher.log.')
    return executable


def ensure_runtime():
    python = find_python()
    if not python: python = install_python()
    logging.info('Found Python: %s',python)
    target = ROOT/'.touchscreen-env/Scripts/python.exe'
    if python != target and not valid_python([str(target)]):
        logging.info('Creating the project Python environment...')
        result = run([python,'-m','venv','--system-site-packages',str(ROOT/'.touchscreen-env')],180)
        if result.returncode: raise RuntimeError('Could not create project environment. Keep the project in a writable folder.')
    if not valid_python([str(target)]): raise RuntimeError('Project Python environment is invalid. See touchscreen-launcher.log.')
    logging.info('Checking Qt, multimedia, OSC and NumPy...')
    if run([target,'-c',CHECK]).returncode:
        logging.info('Downloading/installing missing runtime dependencies. This may take several minutes...')
        result = run([target,'-m','pip','install','--disable-pip-version-check','--index-url','https://pypi.org/simple','--only-binary=:all:','PySide6==6.12.0','python-osc==1.10.2','numpy==2.5.3'],1800)
        if result.returncode or run([target,'-c',CHECK]).returncode:
            raise RuntimeError('Dependency installation failed. Check your internet connection and touchscreen-launcher.log, then run again.')
    return target


def main(admin=False):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only',action='store_true')
    parser.add_argument('--windowed',action='store_true')
    args = parser.parse_args()
    entry = 'admin.py' if admin else 'app.py'
    title = 'TouchScreen Admin' if admin else 'TouchScreen'
    logging.basicConfig(level=logging.INFO,format='%(message)s',handlers=[logging.StreamHandler(sys.stdout),logging.FileHandler(ROOT/('admin-launcher.log' if admin else 'touchscreen-launcher.log'),encoding='utf-8')])
    if os.name == 'nt': ctypes.windll.kernel32.SetDllDirectoryW(None)
    logging.info('%s - checking your setup...',title)
    try:
        for name in (entry,'tuio.py','content_model.py','config.json','content.json','assets/Arabic.ttf'):
            if not (ROOT/name).is_file(): raise RuntimeError(f'Missing project file: {name}. Keep this launcher in the complete TouchScreen project folder.')
        config=json.loads((ROOT/'config.json').read_text(encoding='utf-8-sig'))
        if not admin and not (ROOT/config.get('background_video','Touch screen clean.mp4')).is_file(): raise RuntimeError('Background video is missing. Restore the complete project folder.')
        python = ensure_runtime()
        if args.check_only:
            logging.info('All dependencies are ready.');return 0
        logging.info('Starting %s...',title)
        process = subprocess.Popen([str(python),str(ROOT/entry)]+(['--windowed'] if args.windowed and not admin else []),cwd=ROOT,env=child_env(),creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        # Surface startup failures before this console closes.
        try:
            code = process.wait(timeout=6)
            if code: raise RuntimeError(f'{title} exited during startup ({code}). See the launcher log.')
        except subprocess.TimeoutExpired: pass
        return 0
    except Exception as exc:
        logging.exception('Setup failed: %s',exc)
        if not args.check_only and sys.stdin and sys.stdin.isatty(): input('\nPress Enter to close...')
        return 1

if __name__ == '__main__': raise SystemExit(main())
