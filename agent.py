from app_discovery import handle_app_request
import json
import re
import shutil
import subprocess
import time
from core.paths import safe_path
from tools.file_search import search_files
from pathlib import Path
from ollama import chat
from core.policy import validate_action, needs_confirmation
from tools.appearance import set_theme, set_wallpaper
from tools.display import set_brightness
from tools.system_info import get_system_info
from core.task_runner import run_task
from tools.browser_manager import (
    list_browsers,
    list_browser_profiles,
    open_browser,
)
from tools.desktop_control import (
    list_settings_sections,
    open_settings_section,
)
from tools.window_manager import (
    list_windows,
    format_windows,
    focus_window,
)


ROOT = (Path.home() / "AI-Agent-Workspace").resolve()
ROOT.mkdir(parents=True, exist_ok=True)

MODEL = "qwen3:1.7b"

APPS = {
    "firefox": ["firefox"],
    "chrome": ["google-chrome"],
    "files": ["nautilus"],
    "terminal": ["gnome-terminal"],
    "code": ["code"]
}


def perform(name, args):
    validate_action(name, args)

    if name == "focus_window":
        return focus_window(args["query"])

    if name == "list_windows":
        raw_result = list_windows()

        print(format_windows(raw_result))

        return raw_result

    if name == "list_settings_sections":
        return json.dumps(list_settings_sections())

    if name == "open_settings_section":
        return open_settings_section(args["section"])

    if name == "search_files":
        return search_files(**args)
    
    if name == "list_browsers":
        return json.dumps(list_browsers())

    if name == "list_browser_profiles":
        return json.dumps(
            list_browser_profiles(args["browser"]),
            ensure_ascii=False
        )

    if name == "open_browser":
        return open_browser(
            browser=args["browser"],
            profile=args.get("profile"),
            url=args.get("url")
        )

    if name == "get_system_info":
        return get_system_info(args["info_type"])

    if name == "set_brightness":
        return set_brightness(args["level"])

    if name == "set_theme":
        return set_theme(args["mode"])

    if name == "set_wallpaper":
        return set_wallpaper(args["filename"])

    if name == "open_app":
        app = str(args.get("app", "")).lower()

        if app not in APPS:
            raise ValueError("Unsupported application")

        subprocess.Popen(
            APPS[app],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        return f"Launched {app}"


    path = safe_path(args.get("path", "."))

    if name == "list_files":
        return "\n".join(
            sorted(
                p.name + ("/" if p.is_dir() else "")
                for p in path.iterdir()
            )
        ) or "(empty)"

    if name == "read_file":
        if not path.is_file() or path.stat().st_size > 100000:
            raise ValueError("Not a small text file")
        return path.read_text(encoding="utf-8")

    if name == "create_folder":
        path.mkdir(parents=True, exist_ok=False)
        return f"Created {path}"

    if name == "write_file":
        content = str(args.get("content", ""))
        if len(content) > 100000:
            raise ValueError("Content too long")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as f:
            f.write(content)
        return f"Created {path}"

    if name in ("move_file", "copy_file"):
        dest = safe_path(args["destination"])

        if path == ROOT or dest == ROOT:
            raise ValueError("Cannot move workspace root")
        if not path.exists():
            raise ValueError("Source does not exist")
        if dest.exists():
            raise ValueError("Destination already exists")
        if path.is_dir() and dest.is_relative_to(path):
            raise ValueError("Cannot copy folder into itself")

        dest.parent.mkdir(parents=True, exist_ok=True)

        if name == "move_file":
            shutil.move(str(path), str(dest))
            return f"Moved to {dest}"

        if path.is_dir():
            shutil.copytree(path, dest)
        else:
            shutil.copy2(path, dest)
        return f"Copied to {dest}"

    raise ValueError("Unknown tool")


TOOLS = [


    {
        "type": "function",
        "function": {
            "name": "focus_window",
            "description": (
                "Find an open GNOME application window by "
                "application name or window title and request "
                "accessibility focus. Returns not_found, "
                "ambiguous, unsupported, focus_requested, "
                "or focus_rejected. A focus request does not "
                "guarantee foreground activation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Distinctive application name "
                            "or window title substring"
                        )
                    }
                },
                "required": ["query"]
            }
        }
    },


    {
        "type": "function",
        "function": {
            "name": "list_windows",
            "description": (
                "Discover currently open application windows "
                "on the GNOME desktop using accessibility APIs. "
                "Returns application names and window titles. "
                "This tool is read-only."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },


    {
        "type": "function",
        "function": {
            "name": "list_settings_sections",
            "description": (
                "Discover available GNOME Settings panels. "
                "Use this to find valid sections before navigating."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_settings_section",
            "description": (
                "Open a specific GNOME Settings section, "
                "such as wifi, bluetooth, display, sound, "
                "power, network or keyboard. "
                "Use discovered section identifiers."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "section": {
                        "type": "string",
                        "description": (
                            "Settings section name or identifier"
                        )
                    }
                },
                "required": ["section"]
            }
        }
    },


    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": (
                "Search files inside approved user folders. "
                "Supports recursive searching, file extensions, "
                "filename matching, size filters and file age. "
                "Returns actual file paths and whether results "
                "were truncated. Use before organizing files."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Approved folder, e.g. Downloads"
                    },
                    "extension": {
                        "type": "string",
                        "description": "Optional extension, e.g. pdf"
                    },
                    "name_contains": {
                        "type": "string"
                    },
                    "min_size_kb": {
                        "type": "number"
                    },
                    "max_size_kb": {
                        "type": "number"
                    },
                    "older_than_days": {
                        "type": "number"
                    },
                    "recursive": {
                        "type": "boolean"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_browsers",
            "description": (
                "Discover installed web browsers on Ubuntu. "
                "Use this when the user asks about available browsers."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_browser_profiles",
            "description": (
                "Discover registered local profiles for a browser. "
                "Use before opening a named browser profile. "
                "Returns actual profile names and identifiers."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "browser": {
                        "type": "string",
                        "enum": [
                            "chrome", "chromium",
                            "brave", "edge", "firefox"
                        ]
                    }
                },
                "required": ["browser"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_browser",
            "description": (
                "Launch an installed browser using an existing "
                "local profile, optionally opening an HTTP/HTTPS URL. "
                "Use list_browser_profiles to discover profile names "
                "before calling this tool. Do not call open_app "
                "for requests involving browser profiles."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "browser": {
                        "type": "string",
                        "enum": [
                            "chrome", "chromium",
                            "brave", "edge", "firefox"
                        ]
                    },
                    "profile": {
                        "type": "string",
                        "description": "Existing profile name or identifier"
                    },
                    "url": {
                        "type": "string",
                        "description": "Optional HTTP/HTTPS website URL"
                    }
                },
                "required": ["browser"]
            }
        }
    },


    {
        "type": "function",
        "function": {
            "name": "get_system_info",
            "description": "Get the actual current local time, day, or date from Ubuntu. Always use this tool instead of guessing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "info_type": {
                        "type": "string",
                        "enum": ["time", "day", "date", "datetime"]
                    }
                },
                "required": ["info_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_brightness",
            "description": "Set laptop screen brightness to a percentage from 1 to 100",
            "parameters": {
                "type": "object",
                "properties": {
                    "level": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100
                    }
                },
                "required": ["level"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and folders inside the approved workspace",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a small UTF-8 text file inside the approved workspace",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_folder",
            "description": "Create a new folder inside the approved workspace",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create a new text file without overwriting existing files",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "move_file",
            "description": "Move or rename a file or folder within the approved workspace",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "destination": {"type": "string"}
                },
                "required": ["path", "destination"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "copy_file",
            "description": "Copy a file or folder within the approved workspace",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "destination": {"type": "string"}
                },
                "required": ["path", "destination"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Launch an approved installed desktop application",
            "parameters": {
                "type": "object",
                "properties": {
                    "app": {
                        "type": "string",
                        "enum": list(APPS)
                    }
                },
                "required": ["app"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_theme",
            "description": "Change Ubuntu GNOME appearance to dark or light mode",
            "parameters": {
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["dark", "light"]
                    }
                },
                "required": ["mode"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_wallpaper",
            "description": "Change the Ubuntu GNOME desktop wallpaper using an image filename from the user's Pictures folder",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string"
                    }
                },
                "required": ["filename"]
            }
        }
    }
]


# Explain the current filesystem permissions to the AI.
FILE_TOOL_DESCRIPTIONS = {
    "list_files": (
        "List files and folders in approved Ubuntu user directories. "
        "Supported locations: Desktop, Documents, Downloads, Pictures, "
        "Music, Videos and AI-Agent-Workspace. "
        "Example: path='Downloads'."
    ),
    "read_file": (
        "Read a small UTF-8 text file from any approved user directory. "
        "Example: path='Documents/notes.txt'."
    ),
    "create_folder": (
        "Create a new folder in an approved Ubuntu user directory. "
        "Example: path='Documents/MyProjects'."
    ),
    "write_file": (
        "Create a new UTF-8 text file in any approved Ubuntu user directory. "
        "Use this tool when the user asks you to write, save or create a file. "
        "Example: path='Desktop/quadratic_formula.txt', "
        "content='Quadratic Formula: x = (-b ± √(b² - 4ac)) / (2a)'. "
        "Never merely explain file creation when the user requested it."
    ),
    "move_file": (
        "Move a file or folder between approved Ubuntu user directories. "
        "Example: path='Downloads/report.txt', "
        "destination='Documents/report.txt'."
    ),
    "copy_file": (
        "Copy a file or folder between approved Ubuntu user directories. "
        "Example: path='Documents/notes.txt', "
        "destination='Desktop/notes.txt'."
    ),
}

for tool in TOOLS:
    name = tool["function"]["name"]
    if name in FILE_TOOL_DESCRIPTIONS:
        tool["function"]["description"] = FILE_TOOL_DESCRIPTIONS[name]


def fast_route(user):
    text = user.strip().lower()

    
    text = text.rstrip("?.! ")

    if text in (
        "what time is it",
        "what's the time",
        "whats the time",
        "tell me the time",
        "current time",
        "time",
    ):
        return "get_system_info", {"info_type": "time"}

    if re.fullmatch(
        r"(?:what windows are (?:currently )?open|"
        r"list (?:all )?(?:open )?windows|"
        r"show (?:me )?(?:all )?(?:open )?windows)"
        r"\??",
        user.strip(),
        re.IGNORECASE,
    ):
        return ("list_windows", {})

    if text in (
        "what day is it",
        "what's the day",
        "whats the day",
        "what day is today",
        "what's today",
        "current day",
        "day",
    ):
        return "get_system_info", {"info_type": "day"}

    if text in (
        "what is the date",
        "what's the date",
        "whats the date",
        "today's date",
        "todays date",
        "current date",
        "date",
    ):
        return "get_system_info", {"info_type": "date"}

    if text in (
        "what is the date and time",
        "date and time",
        "current date and time",
    ):
        return "get_system_info", {"info_type": "datetime"}



    if re.fullmatch(
        r"(?:set|change|increase|make)?\s*"
        r"(?:screen\s+)?brightness\s+"
        r"(?:to\s+)?(?:max|maximum|highest|full)",
        text
    ):
        return "set_brightness", {"level": 100}

    if re.fullmatch(
        r"(?:set|change)?\s*"
        r"(?:screen\s+)?brightness\s+"
        r"(?:to\s+)?(?:min|minimum|lowest)",
        text
    ):
        return "set_brightness", {"level": 1}

    match = re.fullmatch(
        r"(?:set|change)?\s*"
        r"(?:screen\s+)?brightness\s+"
        r"(?:to\s+)?(\d{1,3})%?",
        text
    )

    if match:
        return "set_brightness", {
            "level": int(match.group(1))
        }


    # Dark mode
    if text in (
        "dark mode",
        "enable dark mode",
        "switch to dark mode",
        "change to dark mode",
    ):
        return "set_theme", {"mode": "dark"}

    # Light mode
    if text in (
        "light mode",
        "enable light mode",
        "switch to light mode",
        "change to light mode",
    ):
        return "set_theme", {"mode": "light"}

    # Existing fast commands
    patterns = [
        (
            r"(?:create|make) (?:a )?(?:new )?folder "
            r"(?:called|named) (.+)",
            "create_folder",
            "path"
        ),
        (
            r"(?:list|show) (?:all )?(?:the )?files"
            r"(?: (?:in|inside) (.+))?",
            "list_files",
            "path"
        ),
        (
            r"(?:read|show contents of) (?:the )?"
            r"(?:file )?(.+)",
            "read_file",
            "path"
        ),
        (
            r"open (firefox|files|terminal|code)",
            "open_app",
            "app"
        )
    ]

    for pattern, name, key in patterns:
        match = re.fullmatch(pattern, user.strip(), re.I)

        if match:
            value = match.group(1) or "."
            return name, {
                key: value.strip().strip("\"'")
            }

    return None

def execute(name, args):
    import json

    try:
        validate_action(name, args)
    except (PermissionError, ValueError) as error:
        result = f"DENIED: {error}"
        print("Agent >", result)
        return result

    print(
        f"\nProposed: {name}"
        f"({json.dumps(args, ensure_ascii=False)})"
    )

    if needs_confirmation(name):
        approved = (
            input("Allow? [y/N] ")
            .strip()
            .lower() == "y"
        )

        if not approved:
            print("Result: DENIED by user")
            return "DENIED by user"

    try:
        result = perform(name, args)
    except Exception as error:
        result = f"ERROR: {error}"

    if name != "list_windows":
        print("Result:", result)

    return result



SYSTEM_PROMPT = """
GNOME DESKTOP AUTOMATION:

WINDOW ACTIVATION:

Use list_windows to discover open windows.
Use focus_window to request focus for a specific window.

Use distinctive window titles when multiple windows
belong to the same application.

If focus_window returns ambiguous, ask the user
which window to select.

If it returns focus_requested, explain that
the accessibility focus request was accepted,
but foreground activation has not been verified.

Never claim successful window switching without
verification.

Do not use X11-only window-control commands.

WINDOW DISCOVERY:

Use list_windows to discover currently open desktop windows.

The tool returns application names and accessible window titles.

Never invent window names.
Never claim that a window is focused or activated
based only on discovery.

If the requested application has multiple windows,
ask which window the user wants.

Window discovery is read-only.

You can navigate GNOME Settings using registered tools.

Use list_settings_sections to discover installed panels.
Use open_settings_section to open the requested panel.

Examples:
- "Open Wi-Fi settings" -> open_settings_section wifi
- "Open Bluetooth settings" -> open_settings_section bluetooth
- "Open display settings" -> open_settings_section display

Use only available section identifiers.
Do not invent shell commands.
Do not claim that the window opened successfully
unless its appearance has been verified.
A successful launcher result only confirms that
the launch request was submitted.

These tools do not yet provide general mouse clicks,
keyboard input or arbitrary window interaction.
You are an intelligent offline Ubuntu desktop AI agent.

Your purpose is to understand natural-language requests,
reason about them, and perform real actions using registered tools.

FILESYSTEM ACCESS:
You are allowed to manage files inside these user directories:
- Desktop
- Documents
- Downloads
- Pictures
- Music
- Videos
- AI-Agent-Workspace

These locations are approved by the security policy.

PATH EXAMPLES:
Desktop/formula.txt
Documents/notes.txt
Downloads/report.pdf
Pictures/image.jpg

When a user requests a file operation:
1. Understand what they want.
2. Select the appropriate registered tool.
3. Generate the required content if necessary.
4. Call the tool with valid arguments.
5. Wait for the tool result before reporting success.

EXAMPLE:
User: Write the quadratic formula in a file on my Desktop.

Call write_file with:
path: Desktop/quadratic_formula.txt
content: Quadratic Formula

For ax² + bx + c = 0, where a ≠ 0:
x = (-b ± √(b² - 4ac)) / (2a)

BROWSER MANAGEMENT:
You can discover installed browsers and registered local profiles.

Use list_browsers to discover available browsers.
Use list_browser_profiles to find profiles for a browser.
Use open_browser to launch a browser with the selected profile.

For browser requests involving a profile:
1. Discover registered profiles.
2. Match the requested profile name.
3. Call open_browser once with the matched profile.
4. Never invent profile names or directories.
5. Never call open_app as a substitute for opening a profile.

You may explain your reasoning, but complete the action
using the registered tools.

IMPORTANT:
- Perform requested actions instead of only describing them.
- Never claim success without tool confirmation.
- Do not invent terminal commands.
- Never bypass security checks.
- Never attempt operating-system deletion or disk formatting.
- Never execute arbitrary shell commands.
- Explain your reasoning when useful.
- If an action cannot be performed, explain why.
INTELLIGENT FILE SEARCH:

Use search_files when the user asks to find files by:
- File extension or type
- Filename
- File size
- File modification age
- Recursive folder search

Use actual paths returned by search_files.
Never invent filenames.

If the search reports truncated=true, explain that
the results may be incomplete.

Searching is read-only.
Copying, moving, creating, or changing files still
requires the existing permission checks.

When organizing files, search first and then use
registered file tools for approved changes.
"""

messages = [
    {
        "role": "system",
        "content": SYSTEM_PROMPT
    }
]


print(f"Hybrid Ubuntu Agent ({MODEL})")
print(f"Workspace: {ROOT}")
print("Commands: /model small, /model large, exit")

while True:
    try:
        user = input("\nYou > ").strip()

        if user.lower() in ("exit", "quit"):
            break
        if not user:
            continue

        if user.lower() in ("/model small", "/model large"):
            MODEL = (
                "qwen3:1.7b"
                if user.lower().endswith("small")
                else "qwen3:4b"
            )
            print("Model:", MODEL)
            continue

        if handle_app_request(user):
            continue

        multi_step = bool(
            re.search(
                r"\b(?:and then|then|after that|followed by)\b",
                user,
                re.IGNORECASE
            )
        )

        routed = None if multi_step else fast_route(user)

        if routed:
            print("Route > FAST (no LLM)")
            execute(*routed)
            continue

        print(f"Route > AI ({MODEL})")
        messages.append({"role": "user", "content": user})

        complex_task = bool(
            re.search(
                r"\b(then|after|compare|analyze|summarize|organize|plan)\b",
                user,
                re.IGNORECASE,
            )
        )

        run_task(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            execute=execute,
            chat=chat,
            thinking=complex_task,
            options={
                "temperature": 0,
                "num_ctx": 4096,
                "num_predict": 512 if complex_task else 256,
            },
        )

        if len(messages) > 24:
            messages = [messages[0]] + messages[-16:]

    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye")
        break
    except Exception as error:
        print("Error:", error)