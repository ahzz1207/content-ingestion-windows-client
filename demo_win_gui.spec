# PyInstaller spec — demo-win GUI launcher
# Build: pyinstaller demo_win_gui.spec --noconfirm
from pathlib import Path

project_root = Path(SPECPATH).resolve()  # noqa: F821 (PyInstaller injects SPECPATH)
src_dir = project_root / "src"

block_cipher = None

a = Analysis(  # noqa: F821
    [str(project_root / "run_gui.py")],
    pathex=[str(src_dir)],
    binaries=[],
    datas=[],
    hiddenimports=[
        "windows_client.gui.app",
        "windows_client.gui.main_window",
        "windows_client.gui.inline_result_view",
        "windows_client.gui.result_renderer",
        "windows_client.gui.result_workspace_panel",
        "windows_client.gui.library_panel",
        "windows_client.app.cli",
        "windows_client.app.workflow",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "scipy", "pandas"],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="demo-win-gui",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
