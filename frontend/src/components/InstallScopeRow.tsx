interface InstallScopeRowProps {
  project: string;
  hostTag: string;
}

// `.host-row`: the project this board shows (the session's working
// directory; v1 shows one project) and the host name.
export function InstallScopeRow({ project, hostTag }: InstallScopeRowProps) {
  return (
    <div className="host-row">
      <div className="host-row-left">
        <span className="filter-chip readonly" data-testid="install-scope-readonly">
          {project}
        </span>
      </div>
      <div className="host-row-right">
        <span className="host-name mono" data-testid="install-scope-host">
          {hostTag}
        </span>
      </div>
    </div>
  );
}
