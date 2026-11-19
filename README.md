# LIDAR Touch Application

Windows touchscreen exhibit, visual content editor, and dual SLAMTEC Ethernet lidar controller.

## One-click Windows launcher

Double-click `Start TouchScreen.exe` in the project root. Keep it beside `app.py`, `config.json`, `content.json`, the background video and `assets/`. It checks the runtime, creates `.touchscreen-env/`, installs missing runtime packages from PyPI, then starts the exhibit fullscreen. When no supported 64-bit Python 3.11–3.14 is found, it downloads the official Python 3.14.7 installer, verifies its published SHA-256, and installs for the current user without changing PATH. Internet is needed only for missing components. The executable is a launcher for this folder, not a standalone copy of the exhibit.

Setup progress and errors are recorded in `touchscreen-launcher.log`. `Start TouchScreen.exe --check-only` checks/setup dependencies without opening the exhibit. Build the launcher with `./build_launcher.ps1` after installing development requirements. Run `python -m unittest test_launcher` for bootstrap behavior tests.

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

## TouchScreen exhibit

Launch `dist/TouchScreen/TouchScreen.exe`. Copy the entire folder to move the exhibit; Python and Node.js are not required. Keep `_internal`, `config.json`, `content.json`, and `Touch screen clean.mp4` beside the executable.

## Visitor experience

Standby shows the animated city, original heading, and all five systems with their bilingual statistic cards open. Tap a minus or system label to collapse that column. Tap its plus or label to reopen it. Each column toggles independently.

After 20 seconds without input, any closed columns reopen. Active TUIO touches keep the session alive. `idle_return_seconds` in config.json controls the timeout.

Button glows and spaced light sweeps invite interaction. Presses produce a soft confirmation tone and a contact ripple. The supplied cinematic track loops continuously at 50% application volume. `audio.background_volume` and `audio.effects_volume` accept values from 0.0 to 1.0. The `mute` setting controls video audio separately. Windows and speaker volume also affect loudness.

## Controls

Mouse, Windows native touch, and TUIO 1.0/1.1 `/tuio/2Dcur` over OSC/UDP are supported. F11 toggles fullscreen. F2 shows diagnostics and received touch positions. Keys 1–5 toggle the corresponding systems. Home opens all columns. Esc opens any closed columns, or exits if all columns are already open. `TouchScreen.exe --windowed` starts in a window.

## Lidar installation

Use lidar calibration/tracking software to convert detections to normalized TUIO cursor coordinates; the app does not read raw lidar data. Send to this PC's IP address (127.0.0.1 on the same PC), UDP 3333. A second tracker can use port 3334 or the same port with a unique TUIO source identifier. Source names must be distinct. Session IDs are isolated per source; without source messages, distinct sender endpoints are isolated. The app accepts multiple simultaneous contacts and reveals their columns independently. A short same-system debounce limits overlapping duplicate detections.

For network senders, Windows Firewall may need an inbound UDP rule. The app does not modify the firewall. Physically verify sensor coverage, overlapping detections, and calibration at the installation; simulated tests cannot validate those.

## Configuration

Edit config.json beside the executable and restart. `screen` selects a zero-based monitor. `fit: "contain"` preserves the original wide artwork with bars on other aspect ratios; `"stretch"` fills the display. TUIO `coordinate_space: "screen"` maps over the entire screen including bars; `"content"` maps over the artwork. Match this to tracker calibration. `host` and `ports` control UDP listening.

Use `swap_xy`, `invert_x`, and `invert_y` to correct orientation. Per-source settings in `tuio.sources` can override these flags and provide `scale_x`, `scale_y`, `offset_x`, and `offset_y`. For example, `"sources": {"lidar-left": {"scale_x": 0.5}, "lidar-right": {"scale_x": 0.5, "offset_x": 0.5}}` maps two independently calibrated tracker surfaces to the display halves. Prefer configuring both trackers to a shared full-screen surface. Use F2 to check positions.

Protocol: https://www.tuio.org/?specification

## Development

app.py contains the Qt interface and audio. tuio.py handles cursor sources, lifetimes, and frame sequencing. assets contains PNG exports from the provided artwork and audio. Original labels and the heading are embedded in the background video. The `topics` metadata retains system names; topic video paths are no longer used by this in-place reveal experience.

Install with `python -m pip install -r requirements.txt`; launch with `python app.py`. Build the portable Windows folder using build.ps1. Run `python -m unittest test_tuio` for protocol checks and `python verify_app.py` for standby, ten button targets, concurrent UDP reveals, persistent discoveries, inactivity reset, audio loading, and 50% music volume. `python verify_audio_loop.py` checks that music loops across its end. Errors are recorded in touchscreen.log and shown through F2.

## Client reference typography

The default design uses original transparent artwork layers exported from the supplied PDF, which embeds only Bahij TheSansArabic Black, ExtraBold and Plain. Original numeric shapes, raised plus signs, left-hand percentages, AED labels, line breaks, spacing and gradients remain intact for unchanged fields. Font sizes for edited fields use the same supplied fonts. The admin changes only the selected field in its reference layer, preserving surrounding client artwork. Numeric values, raised plus signs and currency labels are separate fields. The layout uses the client reference's 1600 x 696 proportions. The moving background is a cleaned video copy, so its moon, clouds and traffic naturally differ from any single JPEG frame.

The prior editable content was backed up to content.json.before-client-match.json. The client baseline is retained in assets/reference/client-content.json. Run python verify_reference.py to check font families, baseline-layer identity, and isolation of edited number fields. Run python calibrate_reference.py to compare text placement against the supplied JPEG; compression and the animated background prevent an honest claim that the entire screen is pixel-identical to the still image.
