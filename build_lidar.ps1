$ErrorActionPreference = 'Stop'
# Keep saved installation calibration and background models across rebuilds.
$profileBackup = Join-Path $PWD 'lidar_touch\saved-profile-backup'
if (Test-Path -LiteralPath 'dist\DualLidarTouch') {
    New-Item -ItemType Directory -Force -Path $profileBackup | Out-Null
    Get-ChildItem -LiteralPath 'dist\DualLidarTouch' -File | Where-Object { $_.Name -ne 'hardware-check.json' -and $_.Extension -in '.json','.npy' } | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $profileBackup -Force
    }
}
python -m PyInstaller --noconfirm --clean --windowed --onedir --name DualLidarTouch --paths lidar_touch --add-binary "lidar_touch/bin/lidar-bridge.exe;bin" --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineWidgets --exclude-module PySide6.QtPdf lidar_touch\studio.py
if ($LASTEXITCODE -ne 0) { throw 'Lidar calibration build failed' }
$runtimeNames = @('msvcp140.dll','msvcp140_1.dll','msvcp140_2.dll','msvcp140_atomic_wait.dll','msvcp140_codecvt_ids.dll','vcruntime140.dll','vcruntime140_1.dll')
foreach ($runtimeName in $runtimeNames) {
    $runtimeSource = Join-Path $env:WINDIR ('System32\' + $runtimeName)
    foreach ($runtimeDestination in @('dist\DualLidarTouch\_internal','dist\DualLidarTouch\_internal\PySide6','dist\DualLidarTouch\_internal\shiboken6')) {
        Copy-Item -LiteralPath $runtimeSource -Destination $runtimeDestination -Force
    }
}
Copy-Item -LiteralPath "$env:WINDIR\System32\icuuc.dll" -Destination 'dist\DualLidarTouch\_internal\icuuc.dll' -Force
Get-ChildItem -LiteralPath 'dist\DualLidarTouch\_internal' -File -Recurse | ForEach-Object { $_.IsReadOnly = $false }
Copy-Item -LiteralPath 'LIDAR-README.md' -Destination 'dist\DualLidarTouch\README.md' -Force
if (Test-Path -LiteralPath 'lidar_touch\hardware-check.json') { Copy-Item -LiteralPath 'lidar_touch\hardware-check.json' -Destination 'dist\DualLidarTouch\hardware-check.json' -Force }

if (Test-Path -LiteralPath $profileBackup) {
    Get-ChildItem -LiteralPath $profileBackup -File | ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination 'dist\DualLidarTouch' -Force }
}

Copy-Item -LiteralPath 'lidar_touch\THIRD-PARTY-NOTICES.txt' -Destination 'dist\DualLidarTouch' -Force
