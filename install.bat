@echo off
chcp 65001 > nul
echo ===================================================
echo   Dragon PC Master Monitor インストーラー
echo   (c) by youyouboydragon
echo ===================================================
echo.
echo [1/2] 必要なライブラリの確認とセットアップ中...
python -m pip install psutil pywebview flask > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [Info] 既定のPython環境で直接インストールを続行します...
)

echo [2/2] アプリのインストールとショートカット生成中...
python installer.py

echo.
echo ===================================================
echo   インストールが完了しました！
echo   デスクトップの「Dragon PC Master Monitor」から起動できます。
echo ===================================================
pause
