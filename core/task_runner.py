
import json
import time

MAX_ACTIONS = 12
MAX_MODEL_ROUNDS = 16


def action_key(name, args):
    """Identify an action and its arguments."""
    return (
        name,
        json.dumps(
            args,
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        ),
    )


def run_task(
    model,
    messages,
    tools,
    execute,
    chat,
    options=None,
    thinking=False,
):
    """
    Run a multi-step Ollama tool-calling task.

    execute() remains responsible for:
    - security policy validation
    - user confirmation
    - performing registered actions
    """

    completed = {}
    blocked = {}
    actions_used = 0

    for round_number in range(1, MAX_MODEL_ROUNDS + 1):
        print(
            f"\n[Task round {round_number}/{MAX_MODEL_ROUNDS}]"
        )

        start = time.perf_counter()

        response = chat(
            model=model,
            messages=messages,
            tools=tools,
            think=thinking,
            options=options or {},
        )

        print(
            f"Model time: {time.perf_counter() - start:.1f}s"
        )

        message = response.message
        messages.append(message)

        if not message.tool_calls:
            print(
                "Agent >",
                message.content or "(No response)"
            )
            return True

        for call in message.tool_calls:
            name = call.function.name
            args = call.function.arguments

            if not isinstance(args, dict):
                result = "ERROR: Invalid tool arguments"

            else:
                key = action_key(name, args)

                if key in completed:
                    result = (
                        "ALREADY_COMPLETED: This exact action "
                        "succeeded earlier in this task. "
                        f"Previous result: {completed[key]}"
                    )

                elif key in blocked:
                    result = (
                        "PREVIOUSLY_FAILED: This exact action "
                        "was already denied or failed. "
                        f"Previous result: {blocked[key]}"
                    )

                elif actions_used >= MAX_ACTIONS:
                    result = (
                        "TASK_LIMIT_REACHED: Maximum number "
                        "of tool actions reached. "
                        "Stop and report unfinished work."
                    )

                else:
                    actions_used += 1

                    print(
                        f"\n[Action {actions_used}/{MAX_ACTIONS}]"
                    )

                    try:
                        result = str(execute(name, args))
                    except Exception as error:
                        result = f"ERROR: {error}"

                    if result.startswith(("ERROR:", "DENIED:")):
                        blocked[key] = result
                    else:
                        completed[key] = result

            messages.append({
                "role": "tool",
                "tool_name": name,
                "content": result,
            })

        if actions_used >= MAX_ACTIONS:
            print(
                "\nAgent > Action limit reached. "
                "Review the results above for completed "
                "and unfinished work."
            )
            return False

    print(
        "\nAgent > Task stopped: maximum model rounds "
        "reached. Some work may be incomplete."
    )
    return False
