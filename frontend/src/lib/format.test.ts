import { describe, expect, it } from "vitest";
import { formatActivityStamp, formatDateLabel, formatLastTouched, formatTaskCost, taskDisplayName } from "./format";

describe("formatDateLabel", () => {
  it("omits the year when the date falls in the given now's year", () => {
    expect(formatDateLabel("2026-09-28", new Date(Date.UTC(2026, 5, 1)))).toEqual("Sep 28, Mon");
  });

  it("shows the literal year, unparenthesized, when it differs from the given now's year", () => {
    expect(formatDateLabel("2019-01-05", new Date(Date.UTC(2026, 5, 1)))).toEqual("Jan 5 2019, Sat");
  });
});

describe("taskDisplayName", () => {
  it("strips a top-level task folder's date/time prefix", () => {
    expect(taskDisplayName("docs/tasks/2026-09-28-1345-build-kanban-board")).toBe("build-kanban-board");
  });

  it("leaves a sub-task folder's numeric prefix as-is (it has no date to strip)", () => {
    expect(taskDisplayName("docs/tasks/2026-09-28-1345-build-kanban-board/02-heartbeat-hooks")).toBe(
      "02-heartbeat-hooks",
    );
  });
});

describe("formatLastTouched", () => {
  it("says unknown when the task has no log date at all", () => {
    expect(formatLastTouched("", "")).toBe("unknown");
  });

  it("renders relative time from the date and UTC time when a time is present", () => {
    const now = new Date("2026-09-29T10:00:00Z");
    expect(formatLastTouched("2026-09-28", "11:00", now)).toBe("23h ago");
    expect(formatLastTouched("2026-09-29", "09:45", now)).toBe("15m ago");
  });

  it("switches to days from 24 hours on", () => {
    const now = new Date("2026-09-29T10:00:00Z");
    expect(formatLastTouched("2026-09-28", "10:00", now)).toBe("1d ago");
    expect(formatLastTouched("2026-09-28", "09:00", now)).toBe("1d ago");
    expect(formatLastTouched("2026-09-22", "10:00", now)).toBe("7d ago");
  });

  it("falls back to the date label for a future time beyond the skew allowance", () => {
    const now = new Date("2026-09-29T10:00:00Z");
    expect(formatLastTouched("2026-09-29", "10:15", now)).toBe(formatDateLabel("2026-09-29", now));
  });

  it("treats a small future skew as just now", () => {
    const now = new Date("2026-09-29T10:00:00Z");
    expect(formatLastTouched("2026-09-29", "10:02", now)).toBe("0s ago");
  });

  it("falls back to the date label when the time is empty", () => {
    const now = new Date("2026-09-29T10:00:00Z");
    expect(formatLastTouched("2019-01-05", "", now)).toBe(formatDateLabel("2019-01-05", now));
  });
});

describe("formatActivityStamp", () => {
  const now = new Date("2026-09-29T10:00:00Z");

  it("renders relative time for a single-day entry with a time", () => {
    expect(formatActivityStamp("2026-09-29", "09:45", now)).toBe("15m ago");
  });

  it("keeps the raw date when the entry has no time", () => {
    expect(formatActivityStamp("2026-09-23", null, now)).toBe("2026-09-23");
  });

  it("keeps a date range raw even when it carries a time", () => {
    expect(formatActivityStamp("2026-09-28/29", "09:00", now)).toBe("2026-09-28/29");
  });

  it("falls back to the date label for a time beyond the future skew allowance", () => {
    expect(formatActivityStamp("2026-09-29", "10:15", now)).toBe(formatDateLabel("2026-09-29", now));
  });
});

describe("formatTaskCost", () => {
  const base = { usd: null, sessions: 0, shared_sessions: 0 };

  it("shows nothing when no session is linked", () => {
    expect(formatTaskCost({ ...base, state: "none" })).toBeNull();
    expect(formatTaskCost(undefined)).toBeNull();
  });

  it("shows a figure to cents", () => {
    expect(formatTaskCost({ ...base, state: "known", usd: 1.7, sessions: 2 })).toBe("$1.70");
  });

  it("labels shared sessions beside the figure instead of splitting them", () => {
    expect(formatTaskCost({ ...base, state: "known", usd: 1, sessions: 1, shared_sessions: 2 })).toBe("$1.00 + 2 shared");
  });

  it("says shared when every session is shared", () => {
    expect(formatTaskCost({ ...base, state: "shared", shared_sessions: 1 })).toBe("shared session");
  });

  it("says unknown rather than a partial figure", () => {
    expect(formatTaskCost({ ...base, state: "unknown", sessions: 2, shared_sessions: 1 })).toBe("cost unknown");
  });
});
