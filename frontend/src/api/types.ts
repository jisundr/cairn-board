export interface Envelope<T> {
  data: T;
  meta: { generated_at: string };
}

export interface ApiError {
  error: string;
}

export interface ProjectSummary {
  label: string;
  parent: string | null;
}

export interface ProjectsResponse {
  hostname: string;
  projects: ProjectSummary[];
}

// One card per entry in cairn core's `tasks.json`. `column` is the export's
// `phase`; `active` is read from core's live markers; `cost` comes from
// cairn-meter's `usage.json` and is `none` whenever that export is absent.
export type TaskColumn =
  | "parent_tasks"
  | "scoping"
  | "awaiting_approval"
  | "planned"
  | "building"
  | "in_review"
  | "blocked"
  | "done";
export type TaskKind = "build" | "research" | "review";

export interface TaskSubTasksSummary {
  done: number;
  total: number;
}

export type TaskCostState = "none" | "known" | "unknown" | "shared";

export interface TaskCost {
  state: TaskCostState;
  // The sum over sessions bound to this task alone; null unless `known`.
  usd: number | null;
  sessions: number;
  shared_sessions: number;
}

export interface TaskCard {
  project: string;
  folder: string;
  parent: string | null;
  kind: TaskKind;
  goal: string;
  key_info: string;
  last_log_date: string;
  last_log_time: string;
  column: TaskColumn;
  active: boolean;
  needs_attention: boolean;
  done: boolean;
  sub_tasks: TaskSubTasksSummary | null;
  cost: TaskCost;
}

// `tasks.json`'s state: `missing` (core has not written it), `invalid`
// (unreadable), `unsupported` (a schema major this board does not know).
// `usage` is the same for `usage.json`; only `ok` shows cost.
export type ExportStatus = "ok" | "missing" | "invalid" | "unsupported";

export interface BoardPayload {
  status: ExportStatus;
  detail: string;
  generated: string | null;
  usage: ExportStatus;
  usage_detail: string;
  // Tasks left out because their phase is not one this board knows.
  skipped: number;
  cards: TaskCard[];
}

export interface TaskFrontmatter {
  goal?: string;
  paths?: string[];
  done_when?: string;
  out_of_scope?: string[];
  source?: string;
  path?: string;
  key_info?: string;
  flags?: string[];
}

export interface ActivityEntry {
  date: string;
  time: string | null;
  text: string;
}

export interface TaskSubTaskEntry {
  folder: string;
  column: TaskColumn;
  active: boolean;
  needs_attention: boolean;
  goal: string;
}

export interface TaskDoc {
  name: string;
  size: number;
  modified: string;
}

export interface TaskDetail {
  project: string;
  folder: string;
  parent: string | null;
  kind: TaskKind;
  column: TaskColumn;
  active: boolean;
  needs_attention: boolean;
  cost: TaskCost;
  frontmatter: TaskFrontmatter;
  activity: ActivityEntry[] | null;
  draft_content: string | null;
  sub_tasks: TaskSubTaskEntry[] | null;
  docs: TaskDoc[];
}

export interface TaskDocContent {
  content: string;
}
