param([switch]$FullScreen)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$demoUrl = 'http://localhost:4173'
$ready = $false
try { $null = Invoke-RestMethod "$demoUrl/api/config" -TimeoutSec 2; $ready = $true } catch {}
if (!$ready) {
    $nodePath = (Get-Command node -ErrorAction Stop).Source
    $dataFolder = Join-Path $PSScriptRoot 'data'
    New-Item -ItemType Directory -Force -Path $dataFolder | Out-Null
    Start-Process -FilePath $nodePath -ArgumentList @('server.js') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $dataFolder 'server.log') -RedirectStandardError (Join-Path $dataFolder 'server-error.log') | Out-Null
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        Start-Sleep -Milliseconds 250
        try { $null = Invoke-RestMethod "$demoUrl/api/config" -TimeoutSec 1; $ready = $true; break } catch {}
    }
}
if (!$ready) { throw 'The demo could not start. See data/server-error.log.' }
$current = Invoke-RestMethod "$demoUrl/api/config"
if ($current.state.status -eq 'disconnected' -and $current.config.address) {
    $request = @{ transport = $current.config.transport; address = $current.config.address; port = $current.config.port; baud = $current.config.baud } | ConvertTo-Json
    try { $null = Invoke-RestMethod "$demoUrl/api/connect" -Method Post -ContentType 'application/json' -Body $request } catch { Write-Warning 'Connect the sensor from the control screen.' }
}
if ($FullScreen) {
    $displayUrl = "$demoUrl/?display=1"
    $edgePaths = @('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe','C:/Program Files/Microsoft/Edge/Application/msedge.exe')
    $edgePath = $edgePaths | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if ($edgePath) {
        Start-Process -FilePath $edgePath -ArgumentList @("--app=$displayUrl",'--start-fullscreen','--no-first-run')
    } else { Start-Process $displayUrl }
} else { Start-Process $demoUrl }
