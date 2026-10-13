import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { BASE_TITLE } from "../lib/attention";
import { AppHeader } from "./AppHeader";

describe("AppHeader", () => {
  it("shows the attention pill and puts the count in the title", () => {
    render(<AppHeader connected attentionCount={2} />);
    expect(screen.getByTestId("attention-pill")).toHaveTextContent("2 need attention");
    expect(document.title).toBe("(2) cairn board");
  });

  it("hides the pill and restores the base title at zero", () => {
    render(<AppHeader connected attentionCount={0} />);
    expect(screen.queryByTestId("attention-pill")).toBeNull();
    expect(document.title).toBe(BASE_TITLE);
  });

  it("offers refresh only when a handler is given, and disables it while refreshing", () => {
    const onRefresh = vi.fn();
    const { rerender } = render(<AppHeader connected attentionCount={0} />);
    expect(screen.queryByLabelText("Refresh now")).toBeNull();
    rerender(<AppHeader connected attentionCount={0} onRefresh={onRefresh} refreshing />);
    expect(screen.getByLabelText("Refresh now")).toBeDisabled();
  });

  it("marks the status dot as an error when the server is unreachable", () => {
    const { container } = render(<AppHeader connected={false} attentionCount={0} />);
    expect(container.querySelector(".status-dot.err")).not.toBeNull();
  });
});
