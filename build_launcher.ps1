$ErrorActionPreference = 'Stop'
python -m PyInstaller --noconfirm --clean --onefile --console --name 'Start TouchScreen' --distpath '.' --workpath 'build/launcher' --specpath 'build/launcher' --exclude-module PySide6 --exclude-module numpy --exclude-module tkinter touchscreen_launcher.py
if ($LASTEXITCODE -ne 0) { throw 'Launcher build failed' }
