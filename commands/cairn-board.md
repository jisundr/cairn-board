---
description: Starts the cairn-board kanban server for this project in the background and opens it in the browser.
---

1. Start `python3 -u ${CLAUDE_PLUGIN_ROOT}/server.py <project-root>` in the background via `Bash` with `run_in_background`, passing this session's project root as an absolute path. The `-u` flag keeps stdout unbuffered so the readiness line in step 2 reaches the captured output. The port defaults to 4319; append another port number after the project root to change it.
2. Wait for the server's readiness line, `cairn-board: http://<host>:<port>`, rather than a fixed sleep.
3. Open that URL in the default browser (`open` on macOS, `xdg-open` on Linux, `start` on Windows).
4. Report the URL and how to stop the server: it runs as a backgrounded task in this session, so stopping it means ending that task (report its task id).

The board reads `.cairn/export/tasks.json`, which cairn core writes at each session end, and `.cairn/export/usage.json` from cairn-meter when it exists. Without `tasks.json` the page says so and names cairn core; without `usage.json` it shows no cost. The board only reads: it has no write routes and changes nothing under `docs/`, `.harness/` or `.cairn/`.
