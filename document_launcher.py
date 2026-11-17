from pathlib import Path
p=Path('README.md');s=p.read_text(encoding='utf-8');marker='## Start from source';s=s.replace(marker,'''## One-click Windows launcher

Double-click `Start TouchScreen.exe` in the project root. Keep it beside `app.py`, `config.json`, `content.json`, the background video and `assets/`. It checks the runtime, creates `.touchscreen-env/`, installs missing runtime packages from PyPI, then starts the exhibit fullscreen. When no supported 64-bit Python 3.11–3.14 is found, it downloads the official Python 3.14.7 installer, verifies its published SHA-256, and installs for the current user without changing PATH. Internet is needed only for missing components. The executable is a launcher for this folder, not a standalone copy of the exhibit.

Setup progress and errors are recorded in `touchscreen-launcher.log`. `Start TouchScreen.exe --check-only` checks/setup dependencies without opening the exhibit. Build the launcher with `./build_launcher.ps1` after installing development requirements. Run `python -m unittest test_launcher` for bootstrap behavior tests.

'''+marker,1);p.write_text(s,encoding='utf-8')
