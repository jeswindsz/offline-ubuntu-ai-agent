import subprocess
from pathlib import Path

PICTURES = (Path.home() / "Pictures").resolve()

def gsettings_set(schema, key, value):
    result = subprocess.run(
        ["gsettings", "set", schema, key, value],
        capture_output=True,
        text=True,
        timeout=10,
        check=True
    )
    return result

def set_theme(mode):
    if mode not in ("dark", "light"):
        raise ValueError("Unsupported theme")

    value = (
        "prefer-dark" if mode == "dark"
        else "prefer-light"
    )

    gsettings_set(
        "org.gnome.desktop.interface",
        "color-scheme",
        value
    )

    return f"Color scheme set to {mode}"

def set_wallpaper(filename):
    path = (PICTURES / filename).resolve()

    if not path.is_relative_to(PICTURES):
        raise ValueError("Outside approved Pictures folder")

    if not path.is_file():
        raise FileNotFoundError(path)

    if path.suffix.lower() not in (
        ".jpg", ".jpeg", ".png", ".webp"
    ):
        raise ValueError("Unsupported image format")

    uri = path.as_uri()

    for key in ("picture-uri", "picture-uri-dark"):
        gsettings_set(
            "org.gnome.desktop.background",
            key,
            uri
        )

    return f"Wallpaper set to {path.name}"
