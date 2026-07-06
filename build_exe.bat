@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo Local Table Order App - EXE Build
echo ========================================
echo.

where py >nul 2>&1
if %ERRORLEVEL%==0 (
    set PY_CMD=py -3
) else (
    set PY_CMD=python
)

echo Checking Python...
%PY_CMD% --version
if errorlevel 1 (
    echo.
    echo Python was not found.
    echo Please install Python and try again.
    pause
    exit /b 1
)

echo.
echo Installing required packages...
%PY_CMD% -m pip install --upgrade pip
%PY_CMD% -m pip install -r requirements.txt
%PY_CMD% -m pip install pyinstaller

echo.
echo Cleaning old build files...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo Building EXE...
%PY_CMD% -m PyInstaller --noconfirm --clean --onedir --console --name LocalTableOrderApp --add-data "templates;templates" --add-data "static;static" --add-data "data;data" launcher.py

if errorlevel 1 (
    echo.
    echo ========================================
    echo Build failed.
    echo Please check the error message above.
    echo ========================================
    pause
    exit /b 1
)

if not exist "dist\LocalTableOrderApp\LocalTableOrderApp.exe" (
    echo.
    echo ========================================
    echo Build finished, but EXE was not found.
    echo Expected:
    echo dist\LocalTableOrderApp\LocalTableOrderApp.exe
    echo ========================================
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build completed successfully.
echo EXE:
echo dist\LocalTableOrderApp\LocalTableOrderApp.exe
echo ========================================
pause