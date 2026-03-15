from __future__ import annotations

import os
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path


def open_url(url: str) -> bool:
    return webbrowser.open(url)


def open_url_private(url: str) -> tuple[bool, str]:
    if sys.platform == "win32":
        return _open_url_private_windows(url)

    if sys.platform == "darwin":
        commands = [
            ["open", "-na", "Google Chrome", "--args", "--incognito", url],
            ["open", "-na", "Microsoft Edge", "--args", "--inprivate", url],
            ["open", "-na", "Brave Browser", "--args", "--incognito", url],
            ["open", "-na", "Firefox", "--args", "--private-window", url],
        ]
    else:
        commands = [
            ["google-chrome", "--incognito", url],
            ["microsoft-edge", "--inprivate", url],
            ["brave-browser", "--incognito", url],
            ["firefox", "--private-window", url],
        ]

    for command in commands:
        if _run_browser_command(command):
            return True, ""

    return False, "No supported browser was found for private mode."


def _open_url_private_windows(url: str) -> tuple[bool, str]:
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    windows_paths = [
        (
            "Google Chrome",
            ["chrome.exe"],
            [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                str(Path(local_app_data) / "Google" / "Chrome" / "Application" / "chrome.exe"),
            ],
            ["--incognito", url],
        ),
        (
            "Brave",
            ["brave.exe", "brave-browser.exe"],
            [
                r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
                r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
                str(Path(local_app_data) / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe"),
            ],
            ["--incognito", url],
        ),
        (
            "Firefox",
            ["firefox.exe"],
            [
                r"C:\Program Files\Mozilla Firefox\firefox.exe",
                r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
                str(Path(local_app_data) / "Mozilla Firefox" / "firefox.exe"),
            ],
            ["--private-window", url],
        ),
        (
            "Microsoft Edge",
            ["msedge.exe"],
            [
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                str(Path(local_app_data) / "Microsoft" / "Edge" / "Application" / "msedge.exe"),
            ],
            ["--inprivate", url],
        ),
    ]

    for _, names, candidate_paths, args in windows_paths:
        executable = _find_browser_executable(names, candidate_paths)
        if executable and _run_browser_command([executable, *args]):
            return True, ""

    return False, "Could not find Chrome, Edge, Brave, or Firefox to open a private window."


def _find_browser_executable(names: list[str], extra_paths: list[str]) -> str | None:
    for name in names:
        found = shutil.which(name)
        if found:
            return found

    for candidate in extra_paths:
        if candidate and Path(candidate).exists():
            return candidate

    return None


def _run_browser_command(command: list[str]) -> bool:
    try:
        subprocess.Popen(command)
    except OSError:
        return False
    return True
