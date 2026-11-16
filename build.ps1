$ErrorActionPreference = 'Stop'
# Preserve installed administrator edits across executable rebuilds.
$preservedContent = $null
if (Test-Path -LiteralPath 'dist\TouchScreen\content.json') {
    $preservedContent = Get-Content -LiteralPath 'dist\TouchScreen\content.json' -Raw -Encoding UTF8
}
python -m PyInstaller --noconfirm --clean --windowed --onedir --name TouchScreen --add-data 'assets;assets' --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineWidgets --exclude-module PySide6.QtPdf app.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed' }
Copy-Item -LiteralPath 'config.json','content.json','Touch screen clean.mp4','README.md' -Destination 'dist\TouchScreen' -Force
if ($null -ne $preservedContent) {
    [System.IO.File]::WriteAllText((Join-Path $PWD 'dist\TouchScreen\content.json'), $preservedContent, [System.Text.UTF8Encoding]::new($false))
}
New-Item -ItemType Directory -Path 'dist\TouchScreen\content' -Force | Out-Null
'Place topic MP4 files here. See README.md.' | Set-Content 'dist\TouchScreen\content\README.txt'
# Bundle a consistent installed Microsoft runtime; Qt wheels contain older copies.
$runtimeNames = @('msvcp140.dll','msvcp140_1.dll','msvcp140_2.dll','msvcp140_atomic_wait.dll','msvcp140_codecvt_ids.dll','vcruntime140.dll','vcruntime140_1.dll')
foreach ($runtimeName in $runtimeNames) {
    $runtimeSource = Join-Path $env:WINDIR ('System32\' + $runtimeName)
    foreach ($runtimeDestination in @('dist\TouchScreen\_internal','dist\TouchScreen\_internal\PySide6','dist\TouchScreen\_internal\shiboken6')) {
        Copy-Item -LiteralPath $runtimeSource -Destination $runtimeDestination -Force
    }
}
# Qt targets the Windows ICU API. Python 3.14's separately bundled ICU has
# incompatible exports under the same DLL name; bundle the Windows API shim.
Copy-Item -LiteralPath "$env:WINDIR\System32\icuuc.dll" -Destination 'dist\TouchScreen\_internal\icuuc.dll' -Force
# Do not retain the system file's read-only attribute in the portable build.
Get-ChildItem -LiteralPath 'dist\TouchScreen\_internal' -File -Recurse | ForEach-Object { $_.IsReadOnly = $false }
