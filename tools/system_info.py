
from datetime import datetime

def get_system_info(info_type):
    now = datetime.now().astimezone()

    if info_type == "time":
        return now.strftime("The current time is %I:%M:%S %p.")

    if info_type == "day":
        return now.strftime("Today is %A.")

    if info_type == "date":
        return now.strftime("Today's date is %A, %d %B %Y.")

    if info_type == "datetime":
        return now.strftime(
            "Today is %A, %d %B %Y. "
            "The time is %I:%M:%S %p."
        )

    raise ValueError("Unsupported information type")
