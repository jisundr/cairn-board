import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { BoardPayload, TaskCard } from "../api/types";
import { envelope, installFetchMock, serverError } from "../test/mockApi";
import { renderWithClient } from "../test/renderWithClient";
import { Kanban } from "./Kanban";

const noop = () => {};

function task(overrides: Partial<TaskCard> = {}): TaskCard {
  return {
    project: "proj",
    folder: "docs/tasks/2026-10-01-0900-build-alpha",
    parent: null,
    kind: "build",
    goal: "Alpha goal.",
    key_info: "in progress",
    last_log_date: "2026-10-01",
    last_log_time: "",
    column: "planned",
    active: false,
    needs_attention: false,
    done: false,
    sub_tasks: null,
    cost: { state: "none", usd: null, sessions: 0, shared_sessions: 0 },
    ...overrides,
  };
}

function board(overrides: Partial<BoardPayload> = {}): BoardPayload {
  return {
    status: "ok",
    detail: "",
    generated: "2026-10-01T10:00:00Z",
    usage: "missing",
    usage_detail: "",
    skipped: 0,
    cards: [],
    ...overrides,
  };
}

function install(payload: BoardPayload) {
  return installFetchMock({
    "/api/projects": () => envelope({ hostname: "test-host", projects: [{ label: "proj", parent: null }] }),
    "/api/tasks": () => envelope(payload),
  });
}

function renderKanban(overrides: Partial<Parameters<typeof Kanban>[0]> = {}) {
  return renderWithClient(<Kanban openTask={null} drawerTab="details" onOpenTask={noop} {...overrides} />);
}

describe("Kanban", () => {
  it("groups cards into their phase column with counts", async () => {
    install(
      board({
        cards: [
          task({ folder: "docs/tasks/a", column: "building" }),
          task({ folder: "docs/tasks/b", column: "building" }),
          task({ folder: "docs/tasks/c", column: "done" }),
        ],
      }),
    );
    renderKanban();
    await screen.findByTestId("task-card-docs/tasks/a");
    const building = screen.getByText("Building").closest(".kanban-column") as HTMLElement;
    expect(within(building).getByText("2")).toBeInTheDocument();
    expect(within(building).getByTestId("task-card-docs/tasks/b")).toBeInTheDocument();
    const done = screen.getByText("Done").closest(".kanban-column") as HTMLElement;
    expect(within(done).getByTestId("task-card-docs/tasks/c")).toBeInTheDocument();
  });

  it("shows the cost on a card when usage exists", async () => {
    install(
      board({
        usage: "ok",
        cards: [task({ cost: { state: "known", usd: 4.2, sessions: 2, shared_sessions: 0 } })],
      }),
    );
    renderKanban();
    expect(await screen.findByTestId("kcard-cost")).toHaveTextContent("$4.20");
  });

  it("shows no cost and no error when usage is missing", async () => {
    install(board({ cards: [task()] }));
    renderKanban();
    await screen.findByTestId("task-card-docs/tasks/2026-10-01-0900-build-alpha");
    expect(screen.queryByTestId("kcard-cost")).not.toBeInTheDocument();
    expect(screen.queryByTestId("kanban-note")).not.toBeInTheDocument();
    expect(screen.queryByTestId("kanban-error-text")).not.toBeInTheDocument();
  });

  it("names cairn core in the empty state when tasks.json is missing", async () => {
    install(board({ status: "missing", generated: null }));
    renderKanban();
    const state = await screen.findByTestId("kanban-no-export");
    expect(state).toHaveTextContent("cairn core");
    expect(state).toHaveTextContent("Install cairn");
    expect(screen.queryByText("Building")).not.toBeInTheDocument();
  });

  it("refuses an unknown schema major with a message instead of a board", async () => {
    install(board({ status: "unsupported", detail: "tasks.json uses schema 2; this board reads schema 1" }));
    renderKanban();
    const state = await screen.findByTestId("kanban-export-error");
    expect(state).toHaveTextContent("schema 2");
    expect(state).toHaveTextContent("Update cairn-board");
  });

  it("explains hidden cost when usage.json has an unknown schema", async () => {
    install(
      board({
        usage: "unsupported",
        usage_detail: "usage.json uses schema 9; this board reads schema 1",
        cards: [task()],
      }),
    );
    renderKanban();
    expect(await screen.findByTestId("kanban-note")).toHaveTextContent("schema 9");
  });

  it("shows an empty state when the export lists no tasks", async () => {
    install(board());
    renderKanban();
    expect(await screen.findByTestId("kanban-empty")).toBeInTheDocument();
  });

  it("shows a retryable error when the API fails", async () => {
    installFetchMock({
      "/api/projects": () => envelope({ hostname: "h", projects: [{ label: "proj", parent: null }] }),
      "/api/tasks": () => serverError("boom"),
    });
    renderKanban();
    expect(await screen.findByTestId("kanban-error-retry")).toBeInTheDocument();
  });

  it("reports the clicked folder to the caller", async () => {
    install(board({ cards: [task()] }));
    const onOpenTask = vi.fn();
    renderKanban({ onOpenTask });
    fireEvent.click(await screen.findByTestId("task-card-docs/tasks/2026-10-01-0900-build-alpha"));
    expect(onOpenTask).toHaveBeenCalledWith("docs/tasks/2026-10-01-0900-build-alpha", "details");
  });

  it("pages a long column behind See more", async () => {
    const many = Array.from({ length: 25 }, (_, i) => task({ folder: `docs/tasks/t${i}`, column: "planned" }));
    install(board({ cards: many }));
    renderKanban();
    const more = await screen.findByTestId("kanban-see-more-planned");
    expect(document.querySelectorAll(".kcard")).toHaveLength(20);
    fireEvent.click(more);
    await waitFor(() => expect(document.querySelectorAll(".kcard")).toHaveLength(25));
  });

  it("opens the drawer for the open task", async () => {
    install(board({ cards: [task()] }));
    installFetchMock({
      "/api/projects": () => envelope({ hostname: "h", projects: [{ label: "proj", parent: null }] }),
      "/api/tasks": () => envelope(board({ cards: [task()] })),
      "/api/tasks/detail": () => serverError("n/a"),
    });
    renderKanban({ openTask: "docs/tasks/2026-10-01-0900-build-alpha" });
    expect(await screen.findByTestId("task-drawer")).toBeInTheDocument();
  });
});
