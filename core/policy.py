
from pathlib import Path

HOME = Path.home().resolve()
WORKSPACE = (HOME / "AI-Agent-Workspace").resolve()
PICTURES = (HOME / "Pictures").resolve()

ALLOWED_TOOLS = {
    "list_files",
    "read_file",
    "create_folder",
    "write_file",
    "move_file",
    "copy_file",
    "open_app",
    "set_theme",
    "set_wallpaper",
    "set_brightness",
    "get_system_info",
}

READ_ONLY_TOOLS = {"list_files", "read_file", "get_system_info"}

PROTECTED_PATHS = [
    Path("/boot"),
    Path("/etc"),
    Path("/usr"),
    Path("/bin"),
    Path("/sbin"),
    Path("/lib"),
    Path("/lib64"),
    Path("/var"),
    Path("/sys"),
    Path("/proc"),
    Path("/dev"),
    Path("/root"),
]

def within(path, root):
    return path == root or root in path.parents

def validate_action(name, args):

    if name == "get_system_info":
        if args.get("info_type") not in (
            "time", "day", "date", "datetime"
        ):
            raise PermissionError("Invalid information type")
        return

    if name == "set_brightness":
        level = args.get("level")
        if type(level) is not int or not 1 <= level <= 100:
            raise PermissionError("Invalid brightness level")
        return

    if name not in ALLOWED_TOOLS:
        raise PermissionError(
            f"Tool '{name}' is not permitted"
        )

    if not isinstance(args, dict):
        raise PermissionError("Invalid tool arguments")

    if name == "set_theme":
        if args.get("mode") not in ("dark", "light"):
            raise PermissionError("Invalid theme")
        return

    if name == "set_wallpaper":
        filename = args.get("filename")
        if not isinstance(filename, str):
            raise PermissionError("Invalid wallpaper")
        path = (PICTURES / filename).resolve()
        if not within(path, PICTURES):
            raise PermissionError("Wallpaper path denied")
        return

    if name == "open_app":
        return

    for field in ("path", "destination"):
        if field not in args:
            continue

        value = args[field]
        if not isinstance(value, str):
            raise PermissionError("Invalid path")

        path = (WORKSPACE / value).resolve()

        if any(
            within(path, protected)
            for protected in PROTECTED_PATHS
        ):
            raise PermissionError("Protected OS path")

        if not within(path, WORKSPACE):
            raise PermissionError(
                "File access outside workspace denied"
            )

def needs_confirmation(name):
    return name not in READ_ONLY_TOOLS
