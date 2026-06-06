const WorkspaceSwitcher = ({
  workspaces = [],
  activeWorkspaceId = "",
  onChange,
}) => {
  const activeWorkspace = workspaces.find((workspace) => (
    workspace.id === activeWorkspaceId
  ));

  if (workspaces.length === 0) {
    return null;
  }

  if (workspaces.length === 1) {
    return (
      <div className="form-control flex min-h-11 min-w-0 items-center rounded-xl px-3 py-2 text-sm font-semibold">
        <span className="truncate" title={workspaces[0].name}>
          {workspaces[0].name}
        </span>
      </div>
    );
  }

  return (
    <label className="min-w-0">
      <span className="sr-only">Workspace</span>
      <select
        value={activeWorkspaceId || activeWorkspace?.id || ""}
        onChange={(event) => onChange(event.target.value)}
        className="form-control h-11 w-full rounded-xl px-3 py-2 text-sm font-semibold"
        title={
          activeWorkspace
            ? `Viewing: ${activeWorkspace.name}`
            : "Switch workspace"
        }
      >
        {workspaces.map((workspace) => (
          <option key={workspace.id} value={workspace.id}>
            {workspace.name}
          </option>
        ))}
      </select>
    </label>
  );
};

export default WorkspaceSwitcher;
