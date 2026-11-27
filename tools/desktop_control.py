
import os
import shutil
import subprocess


def _check_gnome():
    desktop = os.environ.get(
        "XDG_CURRENT_DESKTOP", ""
    ).lower()

    if "gnome" not in desktop:
        raise RuntimeError(
            "This tool currently supports GNOME only"
        )

    executable = shutil.which("gnome-control-center")

    if not executable:
        raise RuntimeError(
            "GNOME Settings is not installed"
        )

    return executable


def list_settings_sections():
    executable = _check_gnome()

    result = subprocess.run(
        [executable, "--list"],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )

    return sorted({
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip()
        and all(
            ch.isalnum() or ch in "-_"
            for ch in line.strip()
        )
    })


def open_settings_section(section):
    if not isinstance(section, str):
        raise ValueError("Invalid section")

    section = section.strip().lower()

    if not section:
        raise ValueError("Empty section")

    available = list_settings_sections()

    aliases = {
        "wi-fi": "wifi",
        "wireless": "wifi",
        "network settings": "network",
        "bluetooth settings": "bluetooth",
        "display": "display",
        "screen": "display",
        "sound settings": "sound",
        "power settings": "power",
        "keyboard settings": "keyboard",
        "mouse settings": "mouse",
        "background": "background",
        "wallpaper": "background",
    }

    section = aliases.get(section, section)

    if section not in available:
        raise ValueError(
            f"Settings section '{section}' is unavailable. "
            f"Available: {', '.join(available)}"
        )

    executable = _check_gnome()

    subprocess.Popen(
        [executable, section],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    return (
        f"Requested GNOME Settings section: {section}"
    )
