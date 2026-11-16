$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$compiler = Join-Path $PSScriptRoot '.tools/zig-windows-x86_64-0.13.0/zig.exe'
if (!(Test-Path -LiteralPath $compiler)) { throw 'Portable compiler is missing from .tools. See README.md.' }
$sdkRoot = Join-Path $PSScriptRoot 'vendor/rplidar_sdk/sdk'
$sources = @('sl_lidar_driver.cpp','sl_crc.cpp','sl_serial_channel.cpp','sl_lidarprotocol_codec.cpp','sl_async_transceiver.cpp','sl_tcp_channel.cpp','sl_udp_channel.cpp') | ForEach-Object { Join-Path $sdkRoot "src/$_" }
$sources += (Join-Path $sdkRoot 'src/hal/thread.cpp')
$sources += Get-ChildItem -LiteralPath (Join-Path $sdkRoot 'src/dataunpacker') -Recurse -Filter '*.cpp' | ForEach-Object FullName
$sources += Get-ChildItem -LiteralPath (Join-Path $sdkRoot 'src/arch/win32') -Filter '*.cpp' | ForEach-Object FullName
New-Item -ItemType Directory -Force bin | Out-Null
& $compiler c++ -target x86_64-windows-gnu -std=c++14 -O2 -fms-extensions -DWIN32 -DWIN64 -DNOMINMAX "-I$sdkRoot/include" "-I$sdkRoot/src" "-I$sdkRoot/src/dataunpacker" "-I$sdkRoot/src/dataunpacker/unpacker" native/bridge.cpp @sources -lws2_32 -lwinmm -o bin/lidar-bridge.exe
if ($LASTEXITCODE -ne 0) { throw 'Bridge compilation failed' }
