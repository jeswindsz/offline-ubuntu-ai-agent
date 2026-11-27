
import fnmatch
import json
import time
from pathlib import Path

from core.paths import safe_path

MAX_RESULTS = 100
MAX_SCANNED = 10000


def search_files(
    path,
    extension=None,
    name_contains=None,
    min_size_kb=None,
    max_size_kb=None,
    older_than_days=None,
    recursive=True,
):
    root = safe_path(path)

    if not root.is_dir():
        raise ValueError("Search path is not a directory")

    if type(recursive) is not bool:
        raise ValueError("recursive must be true or false")

    if extension is not None:
        if not isinstance(extension, str):
            raise ValueError("Invalid extension")
        extension = extension.strip().lower().lstrip(".")
        if not extension or not extension.isalnum():
            raise ValueError("Invalid extension")

    if name_contains is not None:
        if not isinstance(name_contains, str):
            raise ValueError("Invalid filename filter")
        name_contains = name_contains.casefold()

    for value in (min_size_kb, max_size_kb, older_than_days):
        if value is not None and (
            type(value) not in (int, float)
            or not 0 <= value <= 100000000
        ):
            raise ValueError("Invalid numeric filter")

    if (
        min_size_kb is not None
        and max_size_kb is not None
        and min_size_kb > max_size_kb
    ):
        raise ValueError("Minimum size exceeds maximum")

    results = []
    scanned = 0
    truncated = False
    now = time.time()

    # Path.rglob does not normally traverse directory symlinks.
    # We additionally validate every resolved result.
    iterator = root.rglob("*") if recursive else root.iterdir()

    for candidate in iterator:
        scanned += 1

        if scanned > MAX_SCANNED:
            truncated = True
            break

        try:
            if candidate.is_symlink() or not candidate.is_file():
                continue

            resolved = safe_path(str(candidate))
            if not resolved.is_relative_to(root):
                continue

            stat = resolved.stat()

        except (OSError, PermissionError, ValueError):
            continue

        if extension and resolved.suffix.lower() != "." + extension:
            continue

        if (
            name_contains
            and name_contains not in resolved.name.casefold()
        ):
            continue

        size_kb = stat.st_size / 1024

        if min_size_kb is not None and size_kb < min_size_kb:
            continue

        if max_size_kb is not None and size_kb > max_size_kb:
            continue

        age_days = max(0, (now - stat.st_mtime) / 86400)

        if older_than_days is not None and age_days < older_than_days:
            continue

        results.append({
            "path": str(resolved),
            "name": resolved.name,
            "size_kb": round(size_kb, 2),
            "modified_days_ago": round(age_days, 1),
        })

        if len(results) >= MAX_RESULTS:
            truncated = True
            break

    return json.dumps({
        "root": str(root),
        "matches": results,
        "count": len(results),
        "scanned": scanned,
        "truncated": truncated,
    }, ensure_ascii=False)
