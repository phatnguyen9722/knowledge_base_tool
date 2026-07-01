@echo off
REM Build a standalone Knowledge Base executable (Windows).
REM Output: dist\kb-tool.exe
cd /d "%~dp0"

python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

pyinstaller --onefile --noconsole ^
    --add-data "templates;templates" ^
    --add-data "static;static" ^
    --add-data "config.yaml;." ^
    --name kb-tool ^
    launcher.py
if errorlevel 1 exit /b 1

echo Built: dist\kb-tool.exe
echo Note: posts\ and .kb\ live next to the executable (user data, outside the bundle).
