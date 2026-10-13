# cairn-board

A read-only kanban for a project's cairn tasks. It shows each task in its phase column, which tasks a subagent is working on right now, which ones need a person, and, when [cairn-meter](https://github.com/jisundr/cairn-meter) is installed, what each task cost.

cairn-board reads cairn's exports and the task folders, and never writes to your project, your harness, or `~/.claude/`. It has no write routes; the server refuses anything but `GET`.

## Install

```
/plugin marketplace add jisundr/cairn-3.0-core
/plugin install cairn-board@cairn-marketplace
```

Then, from a project:

```
/cairn-board
```

The command starts the local server on `http://127.0.0.1:4319` and opens it. To use another port, give it after the project root: `python3 server.py <project-root> <port>`.

## What it reads

| File | Written by | Used for |
|---|---|---|
| `<project>/.cairn/export/tasks.json` | cairn core, at each session end | the card list: tasks, phase, parent, sessions |
| `<project>/.cairn/export/usage.json` | cairn-meter | cost per task (optional) |
| `<project>/docs/tasks/<folder>/` | you and cairn | the drawer: `STATE.md` (or `DRAFT.md`), the other `*.md` docs, images |
| `~/.claude/cairn/active/*.active` | cairn core's subagent marker | the "active" badge |

Each export carries `"schema": 1`. A higher schema number than the board knows is refused with a message, not half-read. Unknown keys inside a known schema are ignored.

### States

- **No `tasks.json`**: the page says tasks are written by cairn core and to install cairn. Nothing else breaks.
- **No `usage.json`**: cards show no cost and no error.
- **Unreadable or newer-schema export**: the page names the file and what to do.

### Cost per task

The cost on a card is the sum of `cost_usd` over the sessions bound to that task alone.

- A session bound to several tasks is labelled `shared` and is not split between them. A card with its own sessions and a shared one reads `$1.00 + 1 shared`.
- If any of a task's own sessions has no figure (an unpriced model, or a session `usage.json` does not list), the card reads `cost unknown`, not a partial total.
- A task with no sessions shows no cost.

## Scope in v1

One project: the directory the server is started in. Cards come from that project's `tasks.json`.

## Development

Source commit of the kanban UI and card logic: cairn core `mission-control/` at `0d4e7a3`.

```
python3 -m pytest              # server, export readers, path guards
cd frontend
npm ci
npm run build                  # writes ../static, which is committed
npm test                       # unit tests
npm run e2e                    # Playwright against five seeded scenarios
```

`static/` is the built frontend and ships in the plugin, so installing needs no Node. The e2e run builds first.

See [docs/reading-exports.md](docs/reading-exports.md) for the read-only guarantees.

## License

MIT, see [LICENSE](LICENSE).
