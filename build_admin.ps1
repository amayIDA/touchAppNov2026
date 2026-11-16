$ErrorActionPreference = 'Stop'
python -m PyInstaller --noconfirm --clean --windowed --onedir --name TouchScreenAdmin --add-data 'assets;assets' --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineWidgets --exclude-module PySide6.QtPdf admin.py
if ($LASTEXITCODE -ne 0) { throw 'Admin build failed' }
$runtimeNames = @('msvcp140.dll','msvcp140_1.dll','msvcp140_2.dll','msvcp140_atomic_wait.dll','msvcp140_codecvt_ids.dll','vcruntime140.dll','vcruntime140_1.dll')
foreach ($runtimeName in $runtimeNames) {
    $runtimeSource = Join-Path $env:WINDIR ('System32\' + $runtimeName)
    foreach ($runtimeDestination in @('dist\TouchScreenAdmin\_internal','dist\TouchScreenAdmin\_internal\PySide6','dist\TouchScreenAdmin\_internal\shiboken6')) {
        Copy-Item -LiteralPath $runtimeSource -Destination $runtimeDestination -Force
    }
}
Copy-Item -LiteralPath "$env:WINDIR\System32\icuuc.dll" -Destination 'dist\TouchScreenAdmin\_internal\icuuc.dll' -Force
Get-ChildItem -LiteralPath 'dist\TouchScreenAdmin\_internal' -File -Recurse | ForEach-Object { $_.IsReadOnly = $false }
Copy-Item -LiteralPath 'content.json' -Destination 'dist\TouchScreenAdmin\content.json' -Force
Copy-Item -LiteralPath 'ADMIN-README.md' -Destination 'dist\TouchScreenAdmin\README.md' -Force
