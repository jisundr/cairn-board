import { useEffect, useState } from "react";
import { useBoard, useProjects } from "../api/hooks";
import type { TaskCard as TaskCardData, TaskColumn } from "../api/types";
import { AppHeader } from "../components/AppHeader";
import { InstallScopeRow } from "../components/InstallScopeRow";
import { KanbanIcon } from "../components/icons";
import { PanelError } from "../components/PanelError";
import { StateCard } from "../components/StateCard";
import { TaskCard } from "../components/TaskCard";
import { TaskDrawer } from "../components/TaskDrawer";
import { needsAttentionCount } from "../lib/attention";
import { formatRelativeToNow } from "../lib/format";

type DrawerTab = "details" | "docs";

interface KanbanProps {
  // Drawer URL state lives in App.tsx: a folder path or `null` (closed).
  openTask: string | null;
  drawerTab: DrawerTab;
  onOpenTask: (task: string | null, tab?: DrawerTab) => void;
}

const COLUMNS: { key: TaskColumn; title: string }[] = [
  { key: "parent_tasks", title: "Parent tasks" },
  { key: "scoping", title: "Scoping" },
  { key: "awaiting_approval", title: "Awaiting approval" },
  { key: "planned", title: "Planned" },
  { key: "building", title: "Building" },
  { key: "in_review", title: "In review" },
  { key: "blocked", title: "Blocked" },
  { key: "done", title: "Done" },
];

// Cards page behind a manual "See more" click.
const PAGE_SIZE = 20;

const initialShown = () => Object.fromEntries(COLUMNS.map((c) => [c.key, PAGE_SIZE])) as Record<TaskColumn, number>;

// The board: `/api/tasks` is the card list from cairn core's `tasks.json`,
// grouped into columns client-side. A missing or unreadable export renders
// a state card, never an empty board that looks like "no tasks".
export function Kanban({ openTask, drawerTab, onOpenTask }: KanbanProps) {
  const projects = useProjects();
  const board = useBoard();
  const project = projects.data?.projects[0]?.label ?? "";
  const hostTag = projects.data?.hostname ?? "localhost";
  const payload = board.data;
  const cards = payload?.cards ?? [];

  const [shown, setShown] = useState<Record<TaskColumn, number>>(initialShown);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  useEffect(() => {
    if (payload?.generated) setLastUpdated(new Date(payload.generated));
  }, [payload?.generated]);

  async function handleRefresh() {
    setRefreshing(true);
    try {
      await Promise.allSettled([projects.refetch(), board.refetch()]);
    } finally {
      setRefreshing(false);
    }
  }

  const grouped = Object.fromEntries(COLUMNS.map((c) => [c.key, [] as TaskCardData[]])) as Record<
    TaskColumn,
    TaskCardData[]
  >;
  for (const t of cards) grouped[t.column]?.push(t);

  const notes: string[] = [];
  if (payload?.status === "ok") {
    if (payload.usage === "unsupported" || payload.usage === "invalid") {
      notes.push(`Cost is hidden: ${payload.usage_detail}.`);
    }
    if (payload.skipped > 0) {
      notes.push(`${payload.skipped} task${payload.skipped === 1 ? "" : "s"} skipped: a phase this board does not know.`);
    }
  }

  let body;
  if (board.isError) {
    body = (
      <div
        className="panel err"
        style={{ flexGrow: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: 40 }}
      >
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
          <PanelError
            message="Couldn't load tasks — GET /api/tasks failed"
            onRetry={() => board.refetch()}
            testId="kanban-error"
          />
        </div>
      </div>
    );
  } else if (payload?.status === "missing") {
    body = (
      <StateCard
        data-testid="kanban-no-export"
        icon={<KanbanIcon />}
        title="No task export yet"
        body={
          <>
            Tasks are written by cairn core to <code>.cairn/export/tasks.json</code> at the end of each session.
            Install cairn and finish a session in this project, then refresh.
          </>
        }
      />
    );
  } else if (payload?.status === "unsupported" || payload?.status === "invalid") {
    body = (
      <StateCard
        data-testid="kanban-export-error"
        err
        icon={<KanbanIcon />}
        title={payload.status === "unsupported" ? "This board is older than the export" : "The task export can't be read"}
        body={
          payload.status === "unsupported"
            ? `${payload.detail}. Update cairn-board to read it.`
            : `${payload.detail}. It is rewritten at the next session end by cairn core.`
        }
      />
    );
  } else if (payload?.status === "ok" && cards.length === 0) {
    body = (
      <StateCard
        data-testid="kanban-empty"
        icon={<KanbanIcon />}
        title="No task folders yet"
        body={<>The task export lists no tasks for this project.</>}
      />
    );
  } else {
    body = (
      <div className="kanban-columns" aria-busy={board.isPending}>
        {COLUMNS.map((col) => (
          <div key={col.key} className="kanban-column">
            <div className="kanban-column-head">
              <span className="kanban-column-title">{col.title}</span>
              {!board.isPending && <span className="kanban-column-count">{grouped[col.key].length}</span>}
            </div>
            <div className="kanban-column-cards">
              {board.isPending &&
                [0, 1, 2].map((i) => (
                  <div key={i} className="kcard-skel skel" aria-hidden="true" data-testid="kanban-skel" />
                ))}
              {grouped[col.key].slice(0, shown[col.key]).map((t) => (
                <TaskCard key={t.folder} task={t} onClick={(_project, folder) => onOpenTask(folder, "details")} />
              ))}
              {!board.isPending && grouped[col.key].length > shown[col.key] && (
                <button
                  className="btn-block"
                  onClick={() => setShown((prev) => ({ ...prev, [col.key]: prev[col.key] + PAGE_SIZE }))}
                  data-testid={`kanban-see-more-${col.key}`}
                >
                  See more
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="shell shell-board">
      <AppHeader
        connected={!projects.isError && !board.isError}
        attentionCount={needsAttentionCount(cards)}
        onRefresh={handleRefresh}
        refreshing={refreshing}
        updatedLabel={lastUpdated ? `exported ${formatRelativeToNow(lastUpdated.toISOString())}` : null}
      />

      <InstallScopeRow project={project} hostTag={hostTag} />

      {notes.map((note) => (
        <div key={note} className="host-row" data-testid="kanban-note">
          <span className="mono">{note}</span>
        </div>
      ))}

      {body}

      {openTask && project && (
        <TaskDrawer
          key={openTask}
          project={project}
          folder={openTask}
          tab={drawerTab}
          onClose={() => onOpenTask(null)}
          onTabChange={(tab) => onOpenTask(openTask, tab)}
          onOpenTask={(_project, folder) => onOpenTask(folder, "details")}
        />
      )}
    </div>
  );
}
