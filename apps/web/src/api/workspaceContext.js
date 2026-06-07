export const ACTIVE_WORKSPACE_STORAGE_KEY = "finance-dashboard-active-workspace-id";

export const getActiveWorkspaceId = () => (
  localStorage.getItem(ACTIVE_WORKSPACE_STORAGE_KEY) || ""
);

export const setActiveWorkspaceId = (workspaceId) => {
  const normalizedWorkspaceId = String(workspaceId || "").trim();

  if (!normalizedWorkspaceId) {
    clearActiveWorkspaceId();
    return;
  }

  localStorage.setItem(ACTIVE_WORKSPACE_STORAGE_KEY, normalizedWorkspaceId);
  window.dispatchEvent(new CustomEvent("workspace-changed", {
    detail: { workspaceId: normalizedWorkspaceId },
  }));
};

export const clearActiveWorkspaceId = () => {
  localStorage.removeItem(ACTIVE_WORKSPACE_STORAGE_KEY);
  window.dispatchEvent(new CustomEvent("workspace-changed", {
    detail: { workspaceId: "" },
  }));
};

export const buildWorkspaceHeaders = () => {
  const workspaceId = getActiveWorkspaceId();

  return workspaceId
    ? { "X-Workspace-Id": workspaceId }
    : {};
};
