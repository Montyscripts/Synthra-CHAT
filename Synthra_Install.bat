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
:: Auto-run as administrator
:: ===============================
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if '%errorlevel%' NEQ '0' (
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    echo UAC.ShellExecute "cmd.exe", "/c cd ""%~sdp0"" && %~s0", "", "runas", 1 >> "%temp%\getadmin.vbs"
    "%temp%\getadmin.vbs"
    del "%temp%\getadmin.vbs"
    exit /b
)

echo ########################################################
echo #           SynthraCHAT Automatic Installer            #
echo # This will automatically:                            #
echo # 1. Install all required packages                     #
echo # 2. Create the SynthraCHAT executable                 #
echo #                                                      #
echo # Please wait while the installer runs...              #
echo ########################################################

:: ===============================
:: Check internet connection
:: ===============================
echo Checking internet connection...
ping -n 2 google.com >nul
if errorlevel 1 (
    echo Error: No internet connection detected.
    pause
    exit /b 1
)

:: ===============================
:: Check for Python installation
:: ===============================
where python >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed. Please install Python from:
    echo https://www.python.org/downloads/
    pause
    exit /b 1
)

:: ===============================
:: Upgrade pip and install packages
:: ===============================
echo Installing dependencies...
python -m pip install --upgrade pip setuptools wheel
python -m pip install pyinstaller
python -m pip install -r requirements.txt

if %errorlevel% NEQ 0 (
    echo Failed installing some packages. Trying manual Pillow install...
    python -m pip install pillow==10.3.0 --no-binary :all:
    if %errorlevel% NEQ 0 (
        echo ERROR: Pillow install failed.
        pause
        exit /b 1
    )
)

:: ===============================
:: Build SynthraCHAT Executable
:: ===============================
echo Creating SynthraCHAT executable... Grab a coffee ☕
pyinstaller @pyinstaller.txt SynthraCHAT.py

:: ===============================
:: Check if build succeeded
:: ===============================
if not exist "dist\SynthraCHAT.exe" (
    echo ERROR: Executable creation failed.
    pause
    exit /b 1
)

:: ===============================
:: Move executable to scripts folder
:: ===============================
echo Moving executable to Python Scripts folder...
set "scripts_path=%LOCALAPPDATA%\Programs\Python\Python311\Scripts"
if not exist "%scripts_path%" (
    set "scripts_path=%APPDATA%\Python\Python311\Scripts"
)
if not exist "%scripts_path%" (
    echo Could not find Python Scripts folder. Executable remains in dist folder.
) else (
    move /Y "dist\SynthraCHAT.exe" "%scripts_path%"
    echo SynthraCHAT.exe installed to: %scripts_path%
)

:: ===============================
:: Done!
:: ===============================
echo.
echo ########################################################
echo #       SynthraCHAT is ready to chat! 🚀              #
echo #                                                      #
echo # The executable has been installed to:                #
echo # %scripts_path%\SynthraCHAT.exe                       #
echo ########################################################
pause
exit /b
