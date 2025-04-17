@echo off
setlocal enabledelayedexpansion
color 0C

echo =============================
echo 🔥 SynthraCHAT Uninstaller 🔥
echo =============================

set "CURRENT_DIR=%~dp0"

echo.
echo 📦 Step 1: Uninstalling all pip packages...
pip freeze > "%CURRENT_DIR%piplist.txt"
for /F "delims=" %%i in (%CURRENT_DIR%piplist.txt) do (
    echo Uninstalling %%i ...
    pip uninstall -y %%i
)
del "%CURRENT_DIR%piplist.txt"

echo.
echo 🧹 Step 2: Clearing pip cache...
pip cache purge

echo.
echo 💀 Step 3: Killing SynthraCHAT.exe if running...
taskkill /f /im SynthraCHAT.exe >nul 2>&1

echo.
echo 🗂️ Step 4: Deleting SynthraCHAT directory...

set "FOLDER_NAME=SynthraCHAT-v1.0"
if exist "%CURRENT_DIR%%FOLDER_NAME%" (
    rmdir /s /q "%CURRENT_DIR%%FOLDER_NAME%"
    echo [✓] %FOLDER_NAME% folder nuked.
) else (
    echo [!] %FOLDER_NAME% not found.
)

:: Self-delete setup
set "DELETE_SCRIPT=%temp%\delete_me.bat"
echo @echo off > "%DELETE_SCRIPT%"
echo ping 127.0.0.1 -n 3 >nul >> "%DELETE_SCRIPT%"
echo rmdir /s /q "%CURRENT_DIR%" >> "%DELETE_SCRIPT%"
echo del "%%~f0" >> "%DELETE_SCRIPT%"
echo exit >> "%DELETE_SCRIPT%"

echo.
echo 🧨 Step 5: Goodbye cruel world...
call "%DELETE_SCRIPT%"

exit
