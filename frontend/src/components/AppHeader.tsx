import { useEffect } from "react";
import { BASE_TITLE, titleForCount } from "../lib/attention";
import { AccentPicker } from "./AccentPicker";
import { RefreshIcon } from "./icons";

interface AppHeaderProps {
  connected: boolean;
  // Tasks whose key_info says they need a person; shown as a pill and in
  // the page title.
  attentionCount: number;
  onRefresh?: () => void;
  updatedLabel?: string | null;
  // True while a click-triggered refresh is in flight: the refresh button
  // spins and is disabled.
  refreshing?: boolean;
}

export function AppHeader({ connected, attentionCount, onRefresh, updatedLabel, refreshing }: AppHeaderProps) {
  useEffect(() => {
    document.title = titleForCount(attentionCount);
    return () => {
      document.title = BASE_TITLE;
    };
  }, [attentionCount]);

  return (
    <header className="app">
      <div className="app-left">
        <span className="wordmark">
          <span className="dim">~/ </span>cairn<span className="sep">/</span>
          <span className="sub">board</span>
          <span className="sub-short">board</span>
        </span>
      </div>
      <div className="app-right">
        <AccentPicker />
        {attentionCount > 0 && (
          <span className="attn-pill" data-testid="attention-pill">
            {attentionCount} need attention
          </span>
        )}
        <span
          className={connected ? "status-dot" : "status-dot err"}
          title={connected ? "Connected to the local server" : "Can't reach the local server"}
        />
        {onRefresh && (
          <button
            className={refreshing ? "icon-btn spinning" : "icon-btn"}
            title="Refresh now"
            aria-label="Refresh now"
            aria-busy={refreshing}
            disabled={refreshing}
            onClick={onRefresh}
          >
            <RefreshIcon />
          </button>
        )}
        {updatedLabel && <span className="updated-at mono">{updatedLabel}</span>}
      </div>
    </header>
  );
}
