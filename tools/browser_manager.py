
import configparser
import json
import shutil
import subprocess
from pathlib import Path

HOME = Path.home()

BROWSERS = {
    "chrome": {
        "commands": ["google-chrome", "google-chrome-stable"],
        "folders": [HOME / ".config/google-chrome"],
        "type": "chromium",
    },
    "chromium": {
        "commands": ["chromium", "chromium-browser"],
        "folders": [
            HOME / ".config/chromium",
            HOME / "snap/chromium/common/chromium",
        ],
        "type": "chromium",
    },
    "brave": {
        "commands": ["brave-browser", "brave"],
        "folders": [HOME / ".config/BraveSoftware/Brave-Browser"],
        "type": "chromium",
    },
    "edge": {
        "commands": ["microsoft-edge", "microsoft-edge-stable"],
        "folders": [HOME / ".config/microsoft-edge"],
        "type": "chromium",
    },
    "firefox": {
        "commands": ["firefox"],
        "folders": [
            HOME / ".mozilla/firefox",
            HOME / "snap/firefox/common/.mozilla/firefox",
        ],
        "type": "firefox",
    },
}


def list_browsers():
    result = []

    for name, config in BROWSERS.items():
        executable = next(
            (shutil.which(cmd) for cmd in config["commands"]
             if shutil.which(cmd)),
            None,
        )

        if executable:
            result.append(name)

    return result


def chromium_profiles(folder):
    state_file = folder / "Local State"

    if not state_file.is_file():
        return []

    try:
        data = json.loads(state_file.read_text(encoding="utf-8"))
        info = data.get("profile", {}).get("info_cache", {})
    except (OSError, ValueError, TypeError):
        return []

    profiles = []

    for directory, metadata in info.items():
        if not isinstance(metadata, dict):
            continue

        # Only accept direct child directories.
        if (
            not isinstance(directory, str)
            or directory in ("", ".", "..")
            or Path(directory).name != directory
            or "/" in directory
            or "\\" in directory
        ):
            continue

        profile_dir = folder / directory

        if not profile_dir.is_dir():
            continue

        if profile_dir.is_symlink():
            continue

        profiles.append({
            "name": str(metadata.get("name") or directory),
            "directory": directory,
        })

    return profiles


def firefox_profiles(folder):
    ini = folder / "profiles.ini"

    if not ini.is_file():
        return []

    parser = configparser.ConfigParser(
        interpolation=None
    )

    try:
        parser.read(ini, encoding="utf-8")
    except (OSError, configparser.Error):
        return []

    profiles = []

    for section in parser.sections():
        if not section.startswith("Profile"):
            continue

        name = parser.get(section, "Name", fallback="").strip()
        relative = parser.get(
            section, "IsRelative", fallback="1"
        )
        stored_path = parser.get(
            section, "Path", fallback=""
        ).strip()

        if not name or not stored_path:
            continue

        base = folder if relative == "1" else Path("/")
        profile_path = (base / stored_path).resolve()

        # Only use profiles inside the browser's config root.
        if not profile_path.is_relative_to(folder.resolve()):
            continue

        if not profile_path.is_dir():
            continue

        profiles.append({
            "name": name,
            "directory": str(profile_path),
        })

    return profiles


def list_browser_profiles(browser):
    browser = browser.lower().strip()

    if browser not in BROWSERS:
        raise ValueError("Unsupported browser")

    if browser not in list_browsers():
        raise ValueError(f"{browser} is not installed")

    config = BROWSERS[browser]
    profiles = []

    for folder in config["folders"]:
        if config["type"] == "firefox":
            found = firefox_profiles(folder)
        else:
            found = chromium_profiles(folder)

        for item in found:
            if item not in profiles:
                profiles.append(item)

    return profiles


def resolve_profile(browser, requested):
    profiles = list_browser_profiles(browser)

    matches = [
        profile for profile in profiles
        if requested.casefold() in (
            profile["name"].casefold(),
            profile["directory"].casefold(),
        )
    ]

    if not matches:
        available = ", ".join(
            p["name"] for p in profiles
        ) or "(none discovered)"

        raise ValueError(
            f"Profile '{requested}' not found. "
            f"Available profiles: {available}"
        )

    if len(matches) > 1:
        raise ValueError(
            "Multiple profiles match. Use the exact "
            "profile directory identifier."
        )

    return matches[0]


def open_browser(browser, profile=None, url=None):
    browser = browser.lower().strip()

    if browser not in BROWSERS:
        raise ValueError("Unsupported browser")

    config = BROWSERS[browser]

    executable = next(
        (shutil.which(cmd) for cmd in config["commands"]
         if shutil.which(cmd)),
        None,
    )

    if not executable:
        raise ValueError(f"{browser} is not installed")

    command = [executable]

    if profile:
        selected = resolve_profile(browser, profile)

        if config["type"] == "firefox":
            command += ["-P", selected["name"]]
        else:
            command += [
                f"--profile-directory={selected['directory']}"
            ]

    if url:
        from urllib.parse import urlsplit

        if not isinstance(url, str):
            raise ValueError("Invalid URL")

        parsed = urlsplit(url)

        if (
            parsed.scheme not in ("https", "http")
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise ValueError("Only HTTP/HTTPS URLs are allowed")

        command.append(url)

    subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    return (
        f"Launch requested: {browser}, "
        f"profile={profile or 'default'}, "
        f"url={url or 'none'}"
    )
