@echo off
REM =====================================================
REM Exercise App - Complete Build Script
REM Builds PyInstaller bundle and creates Windows installer
REM =====================================================

echo.
echo =====================================================
echo   Exercise App - Windows Installer Build
echo =====================================================
echo.

REM Check if Inno Setup is installed
if not exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    echo ERROR: Inno Setup 6 not found!
    echo Please install Inno Setup from: https://jrsoftware.org/isdl.php
    echo.
    pause
    exit /b 1
)

echo [1/5] Activating Python environment...
if exist "game_folder1\cardio\venv39\Scripts\activate.bat" (
    call game_folder1\cardio\venv39\Scripts\activate.bat
    echo Python environment activated.
) else (
    echo WARNING: Virtual environment not found at expected location.
    echo Attempting to use system Python...
)
echo.

echo [2/5] Cleaning previous builds...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist
if exist "installer_output" rmdir /s /q installer_output
echo Build directories cleaned.
echo.

echo [3/5] Running PyInstaller...
echo This may take several minutes...
pyinstaller --clean ExerciseApp.spec

if %errorlevel% neq 0 (
    echo.
    echo =====================================================
    echo ERROR: PyInstaller build failed!
    echo =====================================================
    echo.
    echo Common issues:
    echo  - PyInstaller not installed: pip install pyinstaller
    echo  - Missing dependencies: pip install -r requirements.txt
    echo  - Path issues: ensure launcher_all_pages.py exists
    echo.
    pause
    exit /b 1
)
echo PyInstaller build completed successfully.
echo.

echo [4/5] Verifying build output...
if not exist "dist\ExerciseApp\ExerciseApp.exe" (
    echo ERROR: ExerciseApp.exe not found in dist\ExerciseApp\
    echo Build may have failed silently.
    pause
    exit /b 1
)
echo Build verification passed.
echo.

echo [5/5] Building installer with Inno Setup...
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\setup.iss

if %errorlevel% neq 0 (
    echo.
    echo =====================================================
    echo ERROR: Inno Setup build failed!
    echo =====================================================
    echo.
    echo Common issues:
    echo  - setup.iss syntax errors
    echo  - Missing source files in dist\ExerciseApp\
    echo  - Invalid icon file path
    echo.
    pause
    exit /b 1
)
echo Installer created successfully.
echo.

echo =====================================================
echo BUILD SUCCESSFUL!
echo =====================================================
echo.
echo Installer location: installer_output\ExerciseApp_Setup_v1.0.0.exe
echo.
echo Next steps:
echo  1. Test the installer on your machine first
echo  2. Test on a fresh Windows VM (recommended)
echo  3. Distribute the installer to users
echo.
echo Build artifacts:
echo  - Executable bundle: dist\ExerciseApp\
echo  - Installer: installer_output\ExerciseApp_Setup_v1.0.0.exe
echo.
pause
