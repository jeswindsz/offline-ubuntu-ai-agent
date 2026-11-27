
import json
import subprocess
from pathlib import Path


HELPER = (
    Path(__file__).resolve().parent.parent
    / "helpers"
    / "window_discovery.py"
)


def list_windows():
    result = subprocess.run(
        ["/usr/bin/python3", str(HELPER)],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or result.stdout.strip()
            or "Window discovery failed"
        )

    data = json.loads(result.stdout)

    if "error" in data:
        raise RuntimeError(data["error"])

    return json.dumps(data, ensure_ascii=False)


def format_windows(raw_result):
    data = json.loads(raw_result)
    windows = data.get("windows", [])

    if not windows:
        return "No accessible windows found."

    app_names = {
        "code": "Visual Studio Code",
        "ptyxis": "Terminal",
        "gjs": "GNOME Desktop",
    }

    lines = [
        "",
        "=" * 48,
        f"  OPEN WINDOWS ({len(windows)} found)",
        "=" * 48,
    ]

    for index, window in enumerate(windows, 1):
        app = window.get("application", "Unknown")
        title = window.get("title", "(Untitled)")

        app = app_names.get(app, app)

        lines.append(f"\n  {index}. {app}")
        lines.append(f"     {title}")

    lines.append("\n" + "=" * 48)

    return "\n".join(lines)


def focus_window(query):
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Window query is required")

    result = subprocess.run(
        [
            "/usr/bin/python3",
            str(Path(__file__).resolve().parent.parent / "helpers" / "gnome_windows.py"),
            "focus",
            query,
        ],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or result.stdout.strip()
            or "Window focus request failed"
        )

    data = json.loads(result.stdout)

    if data.get("status") == "error":
        raise RuntimeError(data.get("error", "Unknown error"))

    return json.dumps(data, ensure_ascii=False)
