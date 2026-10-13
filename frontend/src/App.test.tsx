import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { App } from "./App";
import { envelope, installFetchMock } from "./test/mockApi";
import { renderWithClient } from "./test/renderWithClient";

const emptyBoard = {
  status: "missing",
  detail: "",
  generated: null,
  usage: "missing",
  usage_detail: "",
  skipped: 0,
  cards: [],
};

describe("App", () => {
  afterEach(() => window.history.replaceState(null, "", "/"));

  it("opens the drawer named in the URL on a hard load", async () => {
    window.history.replaceState(null, "", "/?task=docs/tasks/x&tab=docs");
    installFetchMock({
      "/api/projects": () => envelope({ hostname: "h", projects: [{ label: "proj", parent: null }] }),
      "/api/tasks": () => envelope(emptyBoard),
      "/api/tasks/detail": () => ({ status: 404, body: { error: "task folder not found" } }),
    });
    renderWithClient(<App />);
    const drawer = await screen.findByTestId("task-drawer");
    expect(drawer).toBeInTheDocument();
    expect(screen.getByTestId("drawer-tab-docs")).toHaveClass("active");
    expect(await screen.findByText("Couldn't load this task folder.")).toBeInTheDocument();
  });
});
