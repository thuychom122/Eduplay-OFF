# Installation (EduPlay Studio 1.0.0)

EduPlay Studio 1.0.0 is primarily tested on Windows 10/11.

## Install from source (Windows)

1. Create and activate a virtual environment:

```powershell
python -m venv venv
venv\Scripts\activate
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Configure AI (Groq):

- Set `GROQ_API_KEY` (or `EDUPLAY_GROQ_API_KEY`) in your environment.
- Optional: `GROQ_MODEL` (default: `openai/gpt-oss-20b`)

4. Run the app:

```powershell
python eduplay_studio\app.py
```

## PowerPoint add-in (Windows)

- In EduPlay Studio: Settings → Add-in → Install / Repair Add-in.
- Approve the admin prompt when asked.
- Restart PowerPoint.
- In PowerPoint, find the EduPlay button/tab on the ribbon (it may be under Add-ins).

## Build Windows executable (optional)

This repository contains:
- Cython + Nuitka build script: [build_release.bat](build_release.bat)
- Inno Setup script: [setup.iss](setup.iss)

Windows build notes:
- Run `build_release.bat` on Windows with Python 3.10+.
- Install Visual Studio Build Tools with **Desktop development with C++** and the Windows SDK.
- `build_release.bat` uses `build_nuitka` as an isolated staging/output workspace, then publishes the final standalone folder to `dist\EduPlayStudio`.
- `build_installer.bat` builds `setup.iss` and writes the final installer into `installer\`.
- The output is a standalone directory containing `EduPlayStudio.exe`; Qt WebEngine is intentionally not built as onefile.
- The script does not modify the source tree with generated Cython files.
