$ErrorActionPreference = 'Stop'
python -m PyInstaller --noconfirm --clean --onefile --console --name 'Start TouchScreen Admin' --distpath '.' --workpath 'build/admin-launcher' --specpath 'build/admin-launcher' --exclude-module PySide6 --exclude-module numpy --exclude-module tkinter admin_launcher.py
if ($LASTEXITCODE -ne 0) { throw 'Admin launcher build failed' }
