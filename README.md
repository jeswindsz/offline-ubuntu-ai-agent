# Offline Ubuntu AI Agent — Phase 1

Requires Python 3.10+, Ollama running locally, and an already downloaded `qwen3:4b` model.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python agent.py
```

If your model tag differs, set `AGENT_MODEL=your-model-tag python agent.py`.

All file operations are restricted to `~/AI-Agent-Workspace`. File deletion moves items into `.agent-trash` inside that workspace. Each mutating action requires approval. Application launching is allowlisted and also requires approval.

Examples: `Create a folder called Notes`, `Write a file Notes/todo.txt containing Buy milk`, `List files in Notes`, `Open Firefox`.

Limitations: this is a text-only prototype. No microphone, speech output, arbitrary shell execution, GUI navigation, or general filesystem access. File names containing symlinks are resolved and denied if they point outside the workspace. For stronger isolation against untrusted local processes modifying the workspace concurrently, use OS sandboxing in a later phase.
