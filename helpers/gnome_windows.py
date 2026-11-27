
#!/usr/bin/python3

import json
import sys
from gi.repository import Gio, GLib

BUS = "org.gnome.Shell.Extensions.OfflineAgent"
PATH = "/org/gnome/Shell/Extensions/OfflineAgent"


def call(method, argument=None):
    bus = Gio.bus_get_sync(
        Gio.BusType.SESSION, None
    )

    parameters = (
        GLib.Variant("(s)", (argument,))
        if argument is not None else None
    )

    response = bus.call_sync(
        BUS,
        PATH,
        BUS,
        method,
        parameters,
        GLib.VariantType.new("(s)"),
        Gio.DBusCallFlags.NONE,
        5000,
        None,
    )

    return json.loads(response.unpack()[0])


def focus_by_query(query):
    query = query.strip().casefold()
    if not query:
        raise ValueError("Window query cannot be empty")

    windows = call("ListWindows")["windows"]

    matches = [
        w for w in windows
        if query in (
            w["application"] + " " + w["title"]
        ).casefold()
    ]

    if not matches:
        return {
            "status": "not_found",
            "message": "No matching window found"
        }

    if len(matches) > 1:
        return {
            "status": "ambiguous",
            "matches": matches
        }

    selected = matches[0]

    # Recheck that the ID still identifies the same window.
    latest = call("ListWindows")["windows"]
    if not any(
        w["id"] == selected["id"]
        and w["title"] == selected["title"]
        and w["application"] == selected["application"]
        for w in latest
    ):
        return {
            "status": "stale_window",
            "message": "Window changed; retry discovery"
        }

    result = call("ActivateWindow", selected["id"])

    # Check whether GNOME reports it as focused.
    current = call("ListWindows")["windows"]
    focused = any(
        w["id"] == selected["id"] and w["focused"]
        for w in current
    )

    result["window"] = selected
    result["focused_after_request"] = focused

    if result.get("status") == "activation_requested":
        result["status"] = (
            "focused" if focused else "activation_unverified"
        )

    return result


def main():
    if len(sys.argv) == 2 and sys.argv[1] == "list":
        result = call("ListWindows")

    elif len(sys.argv) == 3 and sys.argv[1] == "focus":
        result = focus_by_query(sys.argv[2])

    else:
        raise ValueError("Invalid helper arguments")

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({
            "status": "error",
            "message": str(error)
        }))
        sys.exit(1)
