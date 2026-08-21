@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
set "ROOT=%CD%"
set "PIP_NO_CACHE_DIR=1"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
set "BUILD_VENV=%CD%\.venv_build"
set "BUILD_PY=%BUILD_VENV%\Scripts\python.exe"
set "STAGE=%ROOT%\build_nuitka\staging"
set "NUITKA_OUT=%ROOT%\build_nuitka\output"
set "DIST_DIR=%NUITKA_OUT%\app.dist"
set "RELEASE_ROOT=%ROOT%\dist"
set "RELEASE_DIR=%RELEASE_ROOT%\EduPlayStudio"
set "SOURCE=%ROOT%\eduplay_studio"

 echo ============================================================
 echo  EduPlay Studio - Cython + Nuitka Windows Build
 echo ============================================================
 echo.
 echo This build requires Windows, Python 3.10+, and MSVC Build Tools.
 echo Install Visual Studio Build Tools with "Desktop development with C++"
 echo and the Windows 10/11 SDK before running this script.
 echo Qt WebEngine is built as a standalone directory, not onefile.
 echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found.
    exit /b 1
)

if not exist "%BUILD_PY%" (
    echo [INFO] Creating build virtual environment...
    python -m venv "%BUILD_VENV%"
    if errorlevel 1 exit /b 1
)

 echo [STEP 1] Installing runtime and build dependencies...
"%BUILD_PY%" -m pip install --upgrade pip --quiet
if errorlevel 1 exit /b 1
if exist "%CD%\requirements.txt" "%BUILD_PY%" -m pip install -r "%CD%\requirements.txt" --quiet
if errorlevel 1 exit /b 1
"%BUILD_PY%" -m pip install Cython Nuitka ordered-set zstandard --quiet
if errorlevel 1 exit /b 1

 echo [STEP 2] Preparing isolated staging tree...
if exist "%CD%\build_nuitka" rmdir /s /q "%CD%\build_nuitka"
mkdir "%STAGE%"
mkdir "%NUITKA_OUT%"
xcopy "%SOURCE%\*" "%STAGE%\" /E /I /H /Y /EXCLUDE:%ROOT%\build_nuitka_exclude.txt >nul
if errorlevel 1 (
    echo [ERROR] Could not copy source into staging.
    exit /b 1
)

 echo [STEP 3] Compiling all stable eduplay modules with Cython...
"%BUILD_PY%" "%ROOT%\tools\compile_cython_modules.py" "%STAGE%"
if errorlevel 1 (
    echo [WARN] Cython could not compile every module; modules left as .py
    echo        will be compiled by Nuitka instead. Continuing the pipeline.
)

 echo [STEP 4] Building standalone executable with Nuitka...
"%BUILD_PY%" -m nuitka ^
  --standalone ^
  --enable-plugin=pyside6 ^
  --windows-console-mode=disable ^
  --assume-yes-for-downloads ^
  --nofollow-import-to=fitz ^
  --nofollow-import-to=pymupdf ^
  --nofollow-import-to=pymupdf.mupdf ^
  --no-deployment-flag=excluded-module-usage ^
  --disable-plugin=pywebview ^
  --include-package=webview ^
  --include-module=pythonnet ^
  --include-package=clr_loader ^
  --include-module=uuid ^
  --output-dir="%NUITKA_OUT%" ^
  --output-filename=EduPlayStudio.exe ^
  --include-package=eduplay ^
  --include-data-dir="%STAGE%\eduplay\resources"=eduplay/resources ^
  --include-data-dir="%STAGE%\assets_bundle"=assets_bundle ^
  --windows-icon-from-ico="%STAGE%\eduplay\resources\icons\icon.ico" ^
  "%STAGE%\app.py"
if errorlevel 1 (
    echo [ERROR] Nuitka build failed.
    exit /b 1
)

if not exist "%DIST_DIR%" set "DIST_DIR=%NUITKA_OUT%\EduPlayStudio.dist"
if not exist "%DIST_DIR%" set "DIST_DIR=%NUITKA_OUT%"
set "THIRD_PARTY=%DIST_DIR%\third_party_py"
echo [STEP 5] Copying third-party Python packages kept out of Nuitka...
if exist "%THIRD_PARTY%" rmdir /s /q "%THIRD_PARTY%"
mkdir "%THIRD_PARTY%"
if errorlevel 1 exit /b 1
xcopy "%BUILD_VENV%\Lib\site-packages\pymupdf" "%THIRD_PARTY%\pymupdf\" /E /I /H /Y >nul
if errorlevel 1 (
    echo [ERROR] Could not copy pymupdf into third_party_py.
    exit /b 1
)
xcopy "%BUILD_VENV%\Lib\site-packages\fitz" "%THIRD_PARTY%\fitz\" /E /I /H /Y >nul
if errorlevel 1 (
    echo [ERROR] Could not copy fitz into third_party_py.
    exit /b 1
)

echo [STEP 6] Publishing standalone directory...
if exist "%RELEASE_DIR%" rmdir /s /q "%RELEASE_DIR%"
if not exist "%RELEASE_ROOT%" mkdir "%RELEASE_ROOT%"
mkdir "%RELEASE_DIR%"
if errorlevel 1 exit /b 1
xcopy "%DIST_DIR%\*" "%RELEASE_DIR%\" /E /I /H /Y >nul
if errorlevel 1 (
    echo [ERROR] Could not publish standalone files to !RELEASE_DIR!.
    exit /b 1
)

set "EXE=%RELEASE_DIR%\EduPlayStudio.exe"
if not exist "%EXE%" set "EXE=%DIST_DIR%\EduPlayStudio.exe"
if not exist "%EXE%" (
    echo [ERROR] Build completed but EduPlayStudio.exe was not found.
    exit /b 1
)
for %%F in ("%EXE%") do set "EXE_SIZE=%%~zF"
echo.
echo [DONE] EduPlayStudio.exe created.
echo Output: %EXE%
echo Published standalone folder: %RELEASE_DIR%
echo Size: %EXE_SIZE% bytes
echo.
exit /b 0
