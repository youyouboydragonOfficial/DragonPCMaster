import os
import sys
import shutil
import subprocess
from pathlib import Path

APP_NAME = "Dragon PC Master Monitor"
DIR_NAME = "DragonPCMaster"

def install():
    print(f"=== {APP_NAME} インストーラー ===")
    
    # 1. Target Directory: %LocalAppData%\DragonPCMaster
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        local_app_data = os.path.expanduser("~\\AppData\\Local")
    
    install_dir = Path(local_app_data) / DIR_NAME
    current_dir = Path(__file__).parent.resolve()

    print(f"[1/4] インストール先ディレクトリの準備: {install_dir}")
    install_dir.mkdir(parents=True, exist_ok=True)

    # 2. Copy application files
    print("[2/4] アプリケーションファイルの配置中...")
    files_to_copy = ["main.py", "hardware_engine.py", "generate_icon.py"]
    for f in files_to_copy:
        src = current_dir / f
        if src.exists():
            shutil.copy2(src, install_dir / f)

    # Copy static folder
    static_src = current_dir / "static"
    static_dst = install_dir / "static"
    if static_src.exists():
        if static_dst.exists():
            shutil.rmtree(static_dst)
        shutil.copytree(static_src, static_dst)

    # 3. Create runner launcher (run_app.vbs / run_app.bat)
    # pythonw.exe executes silently without black terminal window!
    python_exe = sys.executable
    pythonw_exe = python_exe.replace("python.exe", "pythonw.exe")
    if not os.path.exists(pythonw_exe):
        pythonw_exe = python_exe

    # Create vbs runner to hide any console
    vbs_path = install_dir / "launch.vbs"
    main_py_path = install_dir / "main.py"
    with open(vbs_path, "w", encoding="utf-8") as f:
        f.write(f'''Set WshShell = CreateObject("WScript.Shell")\n''')
        f.write(f'''WshShell.CurrentDirectory = "{install_dir}"\n''')
        f.write(f'''WshShell.Run """{pythonw_exe}""" & " """{main_py_path}""", 0, False\n''')

    icon_path = install_dir / "static" / "icon.ico"

    # 4. Create Desktop & Start Menu Shortcuts using PowerShell SpecialFolder
    print("[3/4] デスクトップ＆スタートメニューにショートカット作成中...")

    ps_shortcut_script = f"""
    $WshShell = New-Object -ComObject WScript.Shell
    $desktopDir = [Environment]::GetFolderPath([Environment+SpecialFolder]::Desktop)
    $programsDir = [Environment]::GetFolderPath([Environment+SpecialFolder]::Programs)

    # Desktop Shortcut
    if (Test-Path $desktopDir) {{
        $desktopShortcut = $WshShell.CreateShortcut("$desktopDir\\{APP_NAME}.lnk")
        $desktopShortcut.TargetPath = "wscript.exe"
        $desktopShortcut.Arguments = '"{vbs_path}"'
        $desktopShortcut.WorkingDirectory = "{install_dir}"
        $desktopShortcut.IconLocation = "{icon_path}"
        $desktopShortcut.Description = "最強パソコン状態・温度・ゲーム負荷監視モニター"
        $desktopShortcut.Save()
    }}

    # Start Menu Shortcut
    if (Test-Path $programsDir) {{
        $smShortcut = $WshShell.CreateShortcut("$programsDir\\{APP_NAME}.lnk")
        $smShortcut.TargetPath = "wscript.exe"
        $smShortcut.Arguments = '"{vbs_path}"'
        $smShortcut.WorkingDirectory = "{install_dir}"
        $smShortcut.IconLocation = "{icon_path}"
        $smShortcut.Description = "最強パソコン状態・温度・ゲーム負荷監視モニター"
        $smShortcut.Save()
    }}
    """

    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_shortcut_script], check=True)

    print("[4/4] インストール完了！")
    print(f"デスクトップにショートカット『{APP_NAME}』を追加しました。")
    print("※要件に従い、エクスプローラーへの不要なログ・データ保存は完全に禁止されており、RAM上でのみ安全に動作します。")

if __name__ == "__main__":
    install()
