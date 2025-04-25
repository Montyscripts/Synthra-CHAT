@echo off
SETLOCAL ENABLEEXTENSIONS
cd /d "%~dp0"

:: ===============================
:: Set Text Color to Lime Green
:: ===============================
color 0A

:: ===============================
:: Display SynthraCHAT Coffee Art
:: ===============================
echo       ( (
echo        ) )
echo     ........
echo     ^|      ^|]   ☕ SYNTHRACHAT INSTALLER ☕
echo     \      /
echo      `----'     Brewing cosmic conversations...
echo                 Infusing voices with personality...
echo                 Syncing stardust...
echo.
timeout /t 2 >nul

:: ===============================
:: Check Python installation
:: ===============================
where python >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed. Get it here:
    echo https://www.python.org/downloads/
    pause
    exit /b 1
)

:: ===============================
:: Install Python dependencies
:: ===============================
echo Installing dependencies...
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt

if %errorlevel% NEQ 0 (
    echo ❌ Dependency installation failed!
    pause
    exit /b 1
)

:: ===============================
:: Build SynthraCHAT Executable
:: ===============================
echo.
echo ☕ Creating SynthraCHAT.exe... hold your brew...
python -m PyInstaller --onefile --noconsole ^
--icon=Icon.png ^
--add-data "Button.mp3;." ^
--add-data "Click.mp3;." ^
--add-data "Hover.mp3;." ^
--add-data "Button.png;." ^
--add-data "Wallpaper.png;." ^
--add-data "Icon.png;." ^
--hidden-import=pyaudio ^
--hidden-import=customtkinter ^
--hidden-import=cv2 ^
--hidden-import=PIL ^
--hidden-import=mss ^
--hidden-import=google ^
SynthraCHAT.py

:: ===============================
:: Check if build succeeded
:: ===============================
if not exist "dist\SynthraCHAT.exe" (
    echo ❌ ERROR: Executable build failed.
    pause
    exit /b 1
)

:: ===============================
:: Done!
:: ===============================
echo.
echo ☕ ###################################################
echo ☕   SynthraCHAT is ready to caffeinate your chats!  🚀
echo ☕   Find the .exe in the /dist folder — cheers!      ☕
echo ☕ ###################################################
pause
exit /b
