@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ========================================
echo Local Table Order App exe ビルド
echo ========================================

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

pyinstaller ^
  --noconfirm ^
  --clean ^
  --onedir ^
  --console ^
  --name LocalTableOrderApp ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  launcher.py

echo.
echo ========================================
echo ビルド完了
echo dist\LocalTableOrderApp\LocalTableOrderApp.exe を確認してください
echo ========================================
pause
