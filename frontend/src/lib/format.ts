import type { TaskCost } from "../api/types";

// Display helpers. Log times are UTC; dates are matched as literal UTC days.

export function formatDateLabel(dateStr: string, now: Date = new Date()): string {
  const [year, month, day] = dateStr.split("-").map(Number);
  const d = new Date(Date.UTC(year, month - 1, day));
  const monthName = d.toLocaleString("en-US", { month: "short", timeZone: "UTC" });
  const weekday = d.toLocaleString("en-US", { weekday: "short", timeZone: "UTC" });
  const yearPart = year === now.getUTCFullYear() ? "" : ` ${year}`;
  return `${monthName} ${d.getUTCDate()}${yearPart}, ${weekday}`;
}

export function taskDisplayName(folder: string): string {
  const basename = folder.split("/").pop() ?? folder;
  return basename.replace(/^\d{4}-\d{2}-\d{2}-\d{4}-/, "");
}

const DAY_MS = 24 * 60 * 60 * 1000;
const LAST_TOUCHED_SKEW_MS = 5 * 60 * 1000;

export function formatLastTouched(lastLogDate: string, lastLogTime: string, now: Date = new Date()): string {
  if (!lastLogDate) return "unknown";
  if (!lastLogTime) return formatDateLabel(lastLogDate, now);
  const diffMs = now.getTime() - new Date(`${lastLogDate}T${lastLogTime}:00Z`).getTime();
  // Beyond the skew allowance a future stamp (e.g. a local-time line read as
  // UTC) is untrustworthy, so show the date rather than "0s ago".
  if (diffMs < -LAST_TOUCHED_SKEW_MS) return formatDateLabel(lastLogDate, now);
  if (diffMs >= DAY_MS) return `${Math.floor(diffMs / DAY_MS)}d ago`;
  return formatRelativeToNow(`${lastLogDate}T${lastLogTime}:00Z`, now);
}

// A drawer Activity stamp: relative time for a single-day entry that has a
// time (log times are UTC), else the raw date or range as the log wrote it.
export function formatActivityStamp(date: string, time: string | null, now: Date = new Date()): string {
  if (time && /^\d{4}-\d{2}-\d{2}$/.test(date)) return formatLastTouched(date, time, now);
  return date;
}

export function formatRelativeToNow(iso: string, now: Date = new Date()): string {
  const then = new Date(iso).getTime();
  const diffMs = now.getTime() - then;
  const diffSec = Math.floor(diffMs / 1000);
  if (diffSec < 60) return `${Math.max(0, diffSec)}s ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  return `${diffHr}h ago`;
}

// A task's cost, as the board's rule shows it: a figure only when every
// session bound to the task alone has one, `unknown` when any does not,
// `shared` when every session is shared with another task, and nothing when
// no session is linked. Shared sessions are counted beside a figure, never
// folded into it.
export function formatTaskCost(cost: TaskCost | undefined): string | null {
  if (!cost || cost.state === "none") return null;
  if (cost.state === "unknown") return "cost unknown";
  if (cost.state === "shared") return cost.shared_sessions === 1 ? "shared session" : `${cost.shared_sessions} shared sessions`;
  const figure = `$${(cost.usd ?? 0).toFixed(2)}`;
  return cost.shared_sessions > 0 ? `${figure} + ${cost.shared_sessions} shared` : figure;
}
