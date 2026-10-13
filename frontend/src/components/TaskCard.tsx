import { attentionLabel } from "../lib/attention";
import { formatLastTouched, formatTaskCost, taskDisplayName } from "../lib/format";
import type { TaskCard as TaskCardData } from "../api/types";

interface TaskCardProps {
  task: TaskCardData;
  // Opens the detail drawer on this card's folder.
  onClick?: (project: string, folder: string) => void;
}

// `.kcard`: one task from the export - goal, kind, the parent reference, a
// parent's "N of M done" bar, last-touched, badges, and cost when known.
export function TaskCard({ task, onClick }: TaskCardProps) {
  const subTasks = task.sub_tasks;
  const cost = formatTaskCost(task.cost);
  const progressPct = subTasks && subTasks.total > 0 ? Math.round((subTasks.done / subTasks.total) * 100) : 0;

  return (
    <div
      className="kcard"
      data-testid={`task-card-${task.folder}`}
      onClick={onClick ? () => onClick(task.project, task.folder) : undefined}
      style={onClick ? { cursor: "pointer" } : undefined}
    >
      <div className="kcard-top">
        <span className="kcard-kind">{task.kind}</span>
      </div>
      {task.parent && (
        <span className="kcard-parent" data-testid="kcard-parent">
          <svg viewBox="0 0 24 24" fill="none" strokeWidth="2.5" strokeLinecap="round">
            <path d="M9 6l6 6-6 6" />
          </svg>
          {taskDisplayName(task.parent)}
        </span>
      )}
      <div className="kcard-title">{taskDisplayName(task.folder)}</div>
      <div className="kcard-goal">{task.goal}</div>
      {subTasks && (
        <div className="kcard-progress">
          <div className="hbar-track" style={{ width: 42, height: 5 }}>
            <div className="hbar-fill" style={{ width: `${progressPct}%` }} />
          </div>
          <span className="kcard-progress-label">
            {subTasks.done} of {subTasks.total} done
          </span>
        </div>
      )}
      {cost && (
        <div className="kcard-cost" data-testid="kcard-cost" data-cost-state={task.cost.state}>
          {cost}
        </div>
      )}
      <div className="kcard-foot">
        <span className="kcard-date">last touched {formatLastTouched(task.last_log_date, task.last_log_time)}</span>
        {task.needs_attention && <span className="kcard-attn">{attentionLabel(task.key_info)}</span>}
        {task.active && (
          <span className="kcard-ongoing">
            <span className="status-dot" />
            active
          </span>
        )}
      </div>
    </div>
  );
}
