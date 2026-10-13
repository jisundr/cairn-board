import type { TaskCard } from "../api/types";

export const BASE_TITLE = "~/ cairn/board";

export function needsAttentionCount(tasks: TaskCard[] | undefined): number {
  return (tasks ?? []).filter((t) => t.needs_attention).length;
}

export function titleForCount(count: number): string {
  return count > 0 ? `(${count}) cairn board` : BASE_TITLE;
}

// Short badge label for a needs-attention card, from the same trigger
// phrases core's export uses to set `needs_attention`.
export function attentionLabel(keyInfo: string): string {
  if (/needs-human/.test(keyInfo)) return "needs-human";
  if (/stalled/.test(keyInfo)) return "stalled";
  return "needs attention";
}
