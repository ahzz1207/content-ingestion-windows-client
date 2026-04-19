"""Detect whether Playwright's Chromium binaries are actually installed.

`playwright` the Python package may be present while the separately-downloaded
browser binaries are missing — for example inside a PyInstaller-bundled exe
that relies on the user's `%LOCALAPPDATA%\\ms-playwright` install, or on a
fresh machine where `playwright install chromium` has not run yet. In those
cases Playwright raises a BrowserType.launch error that users struggle to
decode. Preflight it at GUI startup so we can surface a clear remediation.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


INSTALL_COMMAND = "playwright install chromium"


@dataclass(slots=True)
class BrowserPreflightResult:
    ok: bool
    browsers_dir: Path
    reason: str  # short machine-readable code
    hint: str  # user-facing guidance, empty when ok


def resolve_browsers_dir() -> Path:
    env = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if env:
        return Path(env)
    localappdata = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(localappdata) / "ms-playwright"


def check_chromium_available() -> BrowserPreflightResult:
    """Look for at least one usable chromium binary under the expected directory."""
    browsers_dir = resolve_browsers_dir()
    if not browsers_dir.exists():
        return BrowserPreflightResult(
            ok=False,
            browsers_dir=browsers_dir,
            reason="browsers_dir_missing",
            hint=(
                f"找不到 Playwright 浏览器目录：{browsers_dir}\n"
                f"请先在终端执行：{INSTALL_COMMAND}"
            ),
        )
    if sys.platform == "win32":
        patterns = (
            "chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe",
            "chromium-*/chrome-win/chrome.exe",
        )
    elif sys.platform == "darwin":
        patterns = ("chromium-*/chrome-mac/Chromium.app/Contents/MacOS/Chromium",)
    else:
        patterns = ("chromium-*/chrome-linux/chrome",)
    for pattern in patterns:
        for candidate in browsers_dir.glob(pattern):
            if candidate.exists():
                return BrowserPreflightResult(
                    ok=True,
                    browsers_dir=browsers_dir,
                    reason="ok",
                    hint="",
                )
    return BrowserPreflightResult(
        ok=False,
        browsers_dir=browsers_dir,
        reason="chromium_binary_missing",
        hint=(
            f"Playwright 目录存在但缺少 Chromium 浏览器：{browsers_dir}\n"
            f"请在终端执行：{INSTALL_COMMAND}"
        ),
    )
