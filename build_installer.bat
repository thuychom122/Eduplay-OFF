@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
set "ROOT=%CD%"
set "BUILD_SCRIPT=%ROOT%\build_release.bat"
set "SETUP_FILE=%ROOT%\setup.iss"
set "DIST_DIR=%ROOT%\dist\EduPlayStudio"
set "DIST_EXE=%DIST_DIR%\EduPlayStudio.exe"

echo ============================================================
echo  EduPlay Studio - Windows installer
echo ============================================================
echo.

if /I "%~1"=="--skip-build" goto after_build

if not exist "%BUILD_SCRIPT%" (
    echo [ERROR] Missing build_release.bat
    exit /b 1
)
call "%BUILD_SCRIPT%"
if errorlevel 1 (
    echo [ERROR] Standalone build failed.
    exit /b 1
)

:after_build
if not exist "%DIST_EXE%" (
    echo [ERROR] Missing standalone exe: %DIST_EXE%
    echo Run build_release.bat first.
    exit /b 1
)

set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC (
    where ISCC >nul 2>&1
    if not errorlevel 1 for /f "delims=" %%I in ('where ISCC') do if not defined ISCC set "ISCC=%%I"
)
if not defined ISCC (
    echo [ERROR] Inno Setup 6 compiler (ISCC.exe) was not found.
    echo Install Inno Setup 6 and rerun this script.
    exit /b 1
)

echo [STEP] Compiling setup.iss with Inno Setup...
"%ISCC%" "%SETUP_FILE%"
if errorlevel 1 (
    echo [ERROR] Inno Setup compile failed.
    exit /b 1
)

echo.
echo [DONE] Installer written to %ROOT%\installer\
exit /b 0
