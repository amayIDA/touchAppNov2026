from pathlib import Path
p=Path('requirements.txt');s=p.read_text();s+='numpy==2.5.3\n' if 'numpy' not in s else '';p.write_text(s)
p=Path('build.ps1');s=p.read_text();s=s.replace("'config.json','content.json','Touch screen.mp4','Touch screen clean.mp4','README.md'", "'config.json','content.json','Touch screen clean.mp4','README.md'");p.write_text(s)
p=Path('build_lidar.ps1');s=p.read_text();s=s.replace("Copy-Item -LiteralPath 'lidar_touch\\hardware-check.json' -Destination 'dist\\DualLidarTouch\\hardware-check.json' -Force", "if (Test-Path -LiteralPath 'lidar_touch\\hardware-check.json') { Copy-Item -LiteralPath 'lidar_touch\\hardware-check.json' -Destination 'dist\\DualLidarTouch\\hardware-check.json' -Force }");p.write_text(s)
p=Path('README.md');s=p.read_text(encoding='utf-8');s=s.replace('# TouchScreen exhibit', '''# LIDAR Touch Application

Windows touchscreen exhibit, visual content editor, and dual SLAMTEC Ethernet lidar controller.

## Start from source

Use 64-bit Python on Windows (tested with Python 3.14). Run:

```powershell
python -m pip install -r requirements.txt
python lidar_touch/studio.py
python app.py
python admin.py
```

The lidar controller shows Lidar 1 in cyan and Lidar 2 in pink in separate live panels. Connect the sensors, record an empty background, then calibrate each sensor by touching four corner targets followed by 12 random test targets. The corner mapping accounts for rotation and perspective. Passing the tests saves the mapping and enables TUIO to the exhibit on localhost:3333. See [LIDAR-README.md](LIDAR-README.md) for installation and physical alignment, and [ADMIN-README.md](ADMIN-README.md) for editing content.

Build portable Windows applications:

```powershell
./build.ps1
./build_admin.ps1
./build_lidar.ps1
```

Output goes into `dist/TouchScreen`, `dist/TouchScreenAdmin`, and `dist/DualLidarTouch`. Keep each generated folder intact. Executables, installation-specific calibration, background captures, and diagnostics are excluded from Git. The cleaned background video and required design/audio assets are included; the unused large original video is excluded.

## Verification

```powershell
python -m unittest test_tuio
python -m unittest discover -s lidar_touch -p test_engine.py
python lidar_touch/verify_studio.py
```

The guided-flow check uses synthetic contacts, including a rotated mapping and rejection of an incorrect test touch. Hardware checks require the actual sensors; software tests do not establish physical finger accuracy. Optional `verify_demo_parity.py` requires Node.js and the included reference demo.

The supplied reference demo and native SDK bridge retain their notices under `reference_demo/` and `lidar_touch/THIRD-PARTY-NOTICES.txt`. Client design, fonts and audio are included as project assets; no additional redistribution license is granted here.

## TouchScreen exhibit''',1);s=s.replace('Keep `_internal`, `config.json`, and `Touch screen.mp4`','Keep `_internal`, `config.json`, `content.json`, and `Touch screen clean.mp4`');p.write_text(s,encoding='utf-8')
