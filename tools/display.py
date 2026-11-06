
import subprocess

def set_brightness(level):
    level = int(level)

    if not 1 <= level <= 100:
        raise ValueError("Brightness must be between 1 and 100")

    result = subprocess.run(
        ["brightnessctl", "-c", "backlight", "set", f"{level}%"],
        capture_output=True,
        text=True,
        timeout=10,
        check=True
    )

    return f"Brightness set to {level}%"
