import os
import sys
from pathlib import Path

if getattr(sys, "frozen", False) and os.name == "nt":
    localappdata = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(Path(localappdata) / "ms-playwright")

from windows_client.gui.app import launch_gui

launch_gui()
