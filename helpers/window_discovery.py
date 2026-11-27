
#!/usr/bin/python3

import json
import sys
import pyatspi


def find_windows():
    desktop = pyatspi.Registry.getDesktop(0)

    for application in desktop:
        if application is None:
            continue

        app_name = application.name or "Unknown"

        for child in application:
            if child is None:
                continue

            try:
                if child.getRole() not in (
                    pyatspi.ROLE_FRAME,
                    pyatspi.ROLE_DIALOG,
                ):
                    continue

                yield {
                    "application": app_name,
                    "title": child.name or "(Untitled)",
                    "role": child.getRoleName(),
                }, child

            except Exception:
                continue


def discover_windows():
    return [info for info, _ in find_windows()]


def focus_window(query):
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Window query is required")

    query = query.strip().casefold()
    matches = []

    for info, accessible in find_windows():
        searchable = (
            info["application"] + " " + info["title"]
        ).casefold()

        if query in searchable:
            matches.append((info, accessible))

    if not matches:
        return {
            "status": "not_found",
            "message": "No matching accessible window found",
        }

    if len(matches) > 1:
        return {
            "status": "ambiguous",
            "message": "Multiple windows match the query",
            "matches": [info for info, _ in matches],
        }

    info, accessible = matches[0]

    component = accessible.queryComponent()

    if component is None:
        return {
            "status": "unsupported",
            "window": info,
            "message": "Window has no Component interface",
        }

    requested = bool(component.grabFocus())

    return {
        "status": (
            "focus_requested" if requested
            else "focus_rejected"
        ),
        "window": info,
        "message": (
            "Accessibility focus request accepted; "
            "foreground activation is not verified"
            if requested
            else "Accessibility focus request was rejected"
        ),
    }


def main():
    try:
        if len(sys.argv) == 1:
            result = {"windows": discover_windows()}

        elif len(sys.argv) == 3 and sys.argv[1] == "focus":
            result = focus_window(sys.argv[2])

        else:
            raise ValueError("Invalid helper arguments")

        print(json.dumps(result, ensure_ascii=False))

    except Exception as error:
        print(json.dumps({
            "status": "error",
            "error": str(error),
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
