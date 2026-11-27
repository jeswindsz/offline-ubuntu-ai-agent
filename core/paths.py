
import subprocess
from pathlib import Path

HOME = Path.home().resolve()

FOLDER_NAMES = {
    "Desktop": "DESKTOP",
    "Documents": "DOCUMENTS",
    "Downloads": "DOWNLOAD",
    "Pictures": "PICTURES",
    "Music": "MUSIC",
    "Videos": "VIDEOS",
}


def xdg_folder(name):
    result = subprocess.run(
        ["xdg-user-dir", name],
        capture_output=True,
        text=True,
        timeout=5,
        check=True,
    )
    path = Path(result.stdout.strip()).expanduser().resolve()

    if not path.is_dir() or path == HOME:
        raise ValueError(f"Unavailable user folder: {name}")

    return path


def allowed_roots():
    roots = {
        "Workspace": (HOME / "AI-Agent-Workspace").resolve()
    }

    for display_name, xdg_name in FOLDER_NAMES.items():
        try:
            roots[display_name] = xdg_folder(xdg_name)
        except (OSError, ValueError, subprocess.SubprocessError):
            pass

    return roots


def safe_path(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Invalid path")

    roots = allowed_roots()
    raw = value.strip()

    # Accept ~/Documents/file.txt and absolute paths.
    if raw.startswith("~/"):
        candidate = HOME / raw[2:]
    elif Path(raw).is_absolute():
        candidate = Path(raw)
    else:
        parts = Path(raw).parts

        # Accept Desktop/file.txt, Documents/file.txt, etc.
        aliases = {name.lower(): path for name, path in roots.items()}

        if parts and parts[0].lower() in aliases:
            candidate = aliases[parts[0].lower()].joinpath(*parts[1:])
        else:
            # Backward compatibility with the original agent.
            candidate = roots["Workspace"] / raw

    # Resolve existing symlinks and parent-directory traversal.
    path = candidate.resolve(strict=False)

    if not any(
        path == root or root in path.parents
        for root in roots.values()
    ):
        raise PermissionError(
            "Access denied: path is outside approved folders"
        )

    return path
