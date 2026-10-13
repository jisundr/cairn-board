# What cairn-board reads, and what it leaves alone

cairn-board never writes the harness. Its server has no write routes: every `/api/*` route is `GET`, and `POST`, `PUT`, `PATCH` and `DELETE` get a 405. Nothing in the server opens a file for writing.

## Reads

- `.cairn/export/tasks.json` and `.cairn/export/usage.json`, under the project the server was started in.
- `~/.claude/cairn/active/*.active`, for the active badge. A marker counts when it names this project, is under four hours old, and has a schema number of 1 or none.
- Inside the project's `docs/tasks/`: the folder the drawer opens, and only a folder listed in `tasks.json`.

## Path guards

The drawer takes a folder, a file name and an asset path from the browser. Each is resolved and checked before a read:

- the folder resolves inside `<project>/docs/tasks/`, symlinks followed;
- a doc is a direct child of that folder and ends in `.md`;
- an asset must be a `png`, `jpg`, `jpeg`, `gif` or `webp` that still resolves inside the folder (SVG is not served);
- `..` segments, absolute paths, backslashes and NULs are refused.

## Cost rule

Per task: the sum of `cost_usd` over sessions bound to that task alone. A session that more than one task lists is `shared` and is not split. A sole session with a null or missing `cost_usd`, or one listed twice in `usage.json`, makes the task `unknown`. A partial sum is not shown.

## Phase

A card's column is the `phase` in `tasks.json`. A task whose phase is not one of `parent_tasks`, `scoping`, `awaiting_approval`, `planned`, `building`, `in_review`, `blocked`, `done` is left out and counted in a note above the board.
