import os
import sys
from pathlib import Path

if getattr(sys, "frozen", False) and os.name == "nt" and "PLAYWRIGHT_BROWSERS_PATH" not in os.environ:
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(
        Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "ms-playwright"
    )

from windows_client.gui.app import launch_gui

launch_gui()
